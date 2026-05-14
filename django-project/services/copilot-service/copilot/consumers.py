"""
WebSocket consumer for Kitchen Copilot.

Manages session state, calls the LangChain agent, handles tool calls,
and streams ElevenLabs TTS audio back to the browser.
"""
import asyncio
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from langchain_core.messages import HumanMessage, AIMessage

from .agent import invoke_agent, build_recipe_context
from .tts import synthesize_and_send
from . import guard


class CopilotConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.recipe_id = self.scope['url_route']['kwargs']['recipe_id']
        self.session = {
            'phase': 'idle',
            'current_step': 0,
            'ingredients': '',
            'steps': [],
            'recipe_context': '',
            'conversation_history': [],
            'active_timers': [],  # list of label strings in creation order
        }
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'start':
            await self.handle_start(data)
        elif msg_type == 'user_message':
            await self.handle_user_message(data.get('text', ''))
        elif msg_type == 'timer_expired':
            await self.handle_timer_expired(data.get('label', 'timer'))
        elif msg_type == 'stop':
            await self.close()

    async def handle_start(self, data):
        self.session['ingredients'] = data.get('ingredients', '')
        self.session['steps'] = data.get('steps', [])
        self.session['recipe_context'] = build_recipe_context(
            self.session['ingredients'],
            self.session['steps'],
        )
        self.session['phase'] = 'summarize'
        self.session['current_step'] = 0
        self.session['conversation_history'] = []
        self.session['active_timers'] = []

        await self._run_agent('Begin. Summarize the recipe and greet the user.')

    async def handle_user_message(self, text: str):
        loop = asyncio.get_event_loop()
        safe = await loop.run_in_executor(None, guard.is_safe, text)
        if not safe:
            await self.send_json({
                'type': 'text',
                'text': "I can only help with cooking questions. Let's get back to the recipe!",
            })
            return
        self.session['conversation_history'].append(HumanMessage(content=text))
        await self._run_agent(text)

    async def handle_timer_expired(self, label: str):
        if label in self.session['active_timers']:
            self.session['active_timers'].remove(label)
        system_note = f'[SYSTEM: The "{label}" timer has expired. Check in with the user about it.]'
        await self._run_agent(system_note)

    async def _run_agent(self, user_message: str):
        await self.send_json({'type': 'state_change', 'phase': self.session['phase'],
                              'current_step': self.session['current_step']})

        result = await invoke_agent(
            conversation_history=self.session['conversation_history'],
            user_message=user_message,
            recipe_context=self.session['recipe_context'],
            current_step=self.session['current_step'],
            phase=self.session['phase'],
            active_timers=self.session['active_timers'],
        )

        spoken_text = result['text']
        tool_call = result['tool']

        # Record agent response in history, including any tool call so the agent
        # remembers what it did on subsequent turns.
        history_content = result['text']
        if result['tool']:
            history_content += f"\n{json.dumps(result['tool'])}"
        self.session['conversation_history'].append(AIMessage(content=history_content))

        # Handle tool calls before speaking (timer_start should show before audio)
        # end_session is deferred until after TTS so the farewell is heard first
        end_after = tool_call and tool_call.get('tool') == 'end_session'
        if tool_call and not end_after:
            await self._handle_tool(tool_call)

        # Stream TTS audio (or text fallback) to browser
        if spoken_text:
            await synthesize_and_send(spoken_text, self.send_json)

        if end_after:
            await self.close()

    async def _handle_tool(self, tool: dict):
        tool_name = tool.get('tool')

        if tool_name == 'start_timer':
            duration = tool.get('duration_seconds', 60)
            label = tool.get('label', 'Timer')
            if label not in self.session['active_timers']:
                self.session['active_timers'].append(label)
            await self.send_json({
                'type': 'timer_start',
                'label': label,
                'duration_seconds': duration,
            })

        elif tool_name == 'adjust_timer':
            label = tool.get('label', '')
            delta = tool.get('delta_seconds', 0)
            await self.send_json({
                'type': 'timer_adjust',
                'label': label,
                'delta_seconds': delta,
            })

        elif tool_name == 'cancel_timer':
            label = tool.get('label', '')
            if label in self.session['active_timers']:
                self.session['active_timers'].remove(label)
            await self.send_json({
                'type': 'timer_cancel',
                'label': label,
            })

        elif tool_name == 'complete_timer':
            label = tool.get('label', '')
            if label in self.session['active_timers']:
                self.session['active_timers'].remove(label)
            await self.send_json({
                'type': 'timer_complete',
                'label': label,
            })

        elif tool_name == 'mark_step_complete':
            steps = self.session['steps']
            current = self.session['current_step']
            if current + 1 < len(steps):
                self.session['current_step'] = current + 1
                self.session['phase'] = 'cooking'
            else:
                self.session['phase'] = 'complete'
            await self.send_json({
                'type': 'state_change',
                'phase': self.session['phase'],
                'current_step': self.session['current_step'],
            })

    async def send_json(self, data: dict):
        await self.send(text_data=json.dumps(data))
