"""Tests for recipe description generator, ELO utilities, and describe_recipe views."""
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

from recipes.models import Recipe, ApproachELO, DescriptionPreference
from recipes.genai_abtest.elo import expected_score, update_elos, DEFAULT_ELO, ELO_K


OPENAI_SETTINGS = {'OPENAI_API_KEY': 'test-key'}


# ---------------------------------------------------------------------------
# ELO math
# ---------------------------------------------------------------------------

class EloUtilityTests(TestCase):

    def test_expected_score_equal_ratings(self):
        score = expected_score(1000, 1000)
        self.assertAlmostEqual(score, 0.5)

    def test_expected_score_higher_rated_favored(self):
        score = expected_score(1200, 1000)
        self.assertGreater(score, 0.5)

    def test_expected_score_lower_rated_underdog(self):
        score = expected_score(1000, 1200)
        self.assertLess(score, 0.5)

    def test_update_elos_winner_gains_loser_loses(self):
        new_w, new_l = update_elos(1000, 1000)
        self.assertGreater(new_w, 1000)
        self.assertLess(new_l, 1000)

    def test_update_elos_sum_preserved(self):
        # Total ELO in the system should stay constant
        new_w, new_l = update_elos(1000, 1000)
        self.assertEqual(new_w + new_l, 2000)

    def test_update_elos_upset_smaller_gain(self):
        # Favourite losing → bigger swing; underdog winning → smaller gain
        new_w_fav, _ = update_elos(1200, 1000)   # favourite wins (expected)
        new_w_dog, _ = update_elos(1000, 1200)   # underdog wins (upset)
        # Upset gives bigger gain to the winner
        self.assertGreater(new_w_dog - 1000, new_w_fav - 1200)

    def test_default_elo_is_1000(self):
        self.assertEqual(DEFAULT_ELO, 1000)


# ---------------------------------------------------------------------------
# description module (LangChain chain mocked)
# ---------------------------------------------------------------------------

def _make_recipe(user):
    return Recipe.objects.create(
        title='Test Pasta',
        description='A simple pasta.',
        author=user,
        ingredients='pasta\nsalt\nolive oil',
    )


@override_settings(**OPENAI_SETTINGS)
class DescriptionGeneratorTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='chef', password='pass')
        self.recipe = _make_recipe(self.user)

    @patch('recipes.genai_abtest.description._build_chain')
    def test_generate_returns_approach_and_content(self, mock_build_chain):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = 'A tasty pasta.'
        mock_build_chain.return_value = mock_chain

        from recipes.genai_abtest.description import generate
        result = generate(self.recipe, approach='casual')

        self.assertEqual(result['approach'], 'casual')
        self.assertEqual(result['content'], 'A tasty pasta.')

    @patch('recipes.genai_abtest.description._build_chain')
    def test_generate_random_approach_when_none(self, mock_build_chain):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = 'Delicious.'
        mock_build_chain.return_value = mock_chain

        from recipes.genai_abtest.description import generate, APPROACHES
        result = generate(self.recipe, approach=None)

        self.assertIn(result['approach'], APPROACHES)

    @patch('recipes.genai_abtest.description._build_chain')
    def test_generate_invalid_approach_falls_back_to_random(self, mock_build_chain):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = 'Delicious.'
        mock_build_chain.return_value = mock_chain

        from recipes.genai_abtest.description import generate, APPROACHES
        result = generate(self.recipe, approach='nonexistent')

        self.assertIn(result['approach'], APPROACHES)

    @patch('recipes.genai_abtest.description._build_chain')
    def test_compare_returns_two_different_approaches(self, mock_build_chain):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = 'Some text.'
        mock_build_chain.return_value = mock_chain

        from recipes.genai_abtest.description import compare
        result = compare(self.recipe)

        self.assertIn('descriptions', result)
        self.assertEqual(len(result['descriptions']), 2)
        approaches = [d['approach'] for d in result['descriptions']]
        self.assertEqual(len(set(approaches)), 2)  # must be different


# ---------------------------------------------------------------------------
# describe_recipe view
# ---------------------------------------------------------------------------

@override_settings(**OPENAI_SETTINGS)
class DescribeRecipeViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')
        self.recipe = _make_recipe(self.user)
        self.url = reverse('describe_recipe', kwargs={'recipe_id': self.recipe.pk})

    def test_get_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    @patch('recipes.views.description_generator.generate')
    def test_get_single_approach(self, mock_generate):
        mock_generate.return_value = {'approach': 'casual', 'content': 'Yum.'}
        response = self.client.get(self.url, {'approach': 'casual'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['approach'], 'casual')
        mock_generate.assert_called_once_with(self.recipe, 'casual')

    @patch('recipes.views.description_generator.compare')
    def test_get_compare_mode(self, mock_compare):
        mock_compare.return_value = {
            'descriptions': [
                {'approach': 'casual', 'content': 'A.'},
                {'approach': 'poetic', 'content': 'B.'},
            ]
        }
        response = self.client.get(self.url, {'compare': 'true'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('descriptions', data)
        self.assertEqual(len(data['descriptions']), 2)

    def test_post_saves_preference_and_updates_elo(self):
        payload = {'preferred_approach': 'casual', 'rejected_approach': 'professional'}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'saved')
        self.assertIn('casual', data['elo'])
        self.assertIn('professional', data['elo'])

        # Winner should have rating > 1000, loser < 1000
        self.assertGreater(data['elo']['casual'], DEFAULT_ELO)
        self.assertLess(data['elo']['professional'], DEFAULT_ELO)

        # Preference persisted
        pref = DescriptionPreference.objects.get(user=self.user, recipe=self.recipe)
        self.assertEqual(pref.preferred_approach, 'casual')

        # ELO rows created
        self.assertTrue(ApproachELO.objects.filter(feature='description', approach='casual').exists())

    def test_post_invalid_approach_returns_400(self):
        payload = {'preferred_approach': 'casual', 'rejected_approach': 'invalid'}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_post_same_approaches_returns_400(self):
        payload = {'preferred_approach': 'casual', 'rejected_approach': 'casual'}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_post_invalid_json_returns_400(self):
        response = self.client.post(self.url, data='not-json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_post_upserts_preference(self):
        payload = {'preferred_approach': 'casual', 'rejected_approach': 'professional'}
        self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        # Second post with different preference
        payload2 = {'preferred_approach': 'poetic', 'rejected_approach': 'casual'}
        self.client.post(self.url, data=json.dumps(payload2), content_type='application/json')
        # Should still be only one record
        self.assertEqual(DescriptionPreference.objects.filter(user=self.user, recipe=self.recipe).count(), 1)
        pref = DescriptionPreference.objects.get(user=self.user, recipe=self.recipe)
        self.assertEqual(pref.preferred_approach, 'poetic')


# ---------------------------------------------------------------------------
# describe_rankings view
# ---------------------------------------------------------------------------

class DescribeRankingsViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('describe_rankings')

    def test_empty_rankings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['rankings'], [])

    def test_rankings_ordered_by_elo_desc(self):
        ApproachELO.objects.create(feature='description', approach='casual', rating=1020)
        ApproachELO.objects.create(feature='description', approach='poetic', rating=1050)
        ApproachELO.objects.create(feature='description', approach='professional', rating=980)

        response = self.client.get(self.url)
        data = json.loads(response.content)
        ratings = [r['rating'] for r in data['rankings']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))

    def test_rankings_excludes_other_features(self):
        ApproachELO.objects.create(feature='other_feature', approach='casual', rating=9999)
        ApproachELO.objects.create(feature='description', approach='poetic', rating=1010)

        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(len(data['rankings']), 1)
        self.assertEqual(data['rankings'][0]['approach'], 'poetic')
