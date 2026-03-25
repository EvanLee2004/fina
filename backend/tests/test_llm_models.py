"""
模型选择相关测试。
"""

from __future__ import annotations

import unittest

from services.integrations.llm_service import get_ai_model_catalog, resolve_ai_model
from core.config import settings


class LlmModelSelectionTests(unittest.TestCase):
    """
    验证多模型配置解析逻辑。
    """

    def setUp(self) -> None:
        self.original_model = settings.AI_MODEL
        self.original_allowed = settings.AI_ALLOWED_MODELS

    def tearDown(self) -> None:
        settings.AI_MODEL = self.original_model
        settings.AI_ALLOWED_MODELS = self.original_allowed

    def test_resolve_ai_model_falls_back_to_default(self) -> None:
        settings.AI_MODEL = "deepseek-chat"
        settings.AI_ALLOWED_MODELS = ""
        self.assertEqual(resolve_ai_model(), "deepseek-chat")

    def test_resolve_ai_model_checks_whitelist(self) -> None:
        settings.AI_MODEL = "deepseek-chat"
        settings.AI_ALLOWED_MODELS = "deepseek-chat,gpt-4o-mini"
        self.assertEqual(resolve_ai_model("gpt-4o-mini"), "gpt-4o-mini")

        with self.assertRaises(ValueError):
            resolve_ai_model("qwen-max")

    def test_model_catalog_contains_examples(self) -> None:
        settings.AI_MODEL = "deepseek-chat"
        settings.AI_ALLOWED_MODELS = "deepseek-chat,gpt-4o-mini"
        catalog = get_ai_model_catalog()
        self.assertEqual(catalog["default_model"], "deepseek-chat")
        self.assertIn("gpt-4o-mini", catalog["configured_allowed_models"])
        self.assertIn("qwen-max", catalog["example_models"])
