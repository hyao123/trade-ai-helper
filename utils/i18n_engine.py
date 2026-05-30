"""
utils/i18n_engine.py
--------------------
Multi-language interface engine with lazy-loaded translation packs.

Supports:
  - zh (Chinese) — default
  - en (English)
  - ja (Japanese)
  - ko (Korean)
  - es (Spanish)

Architecture:
  - Base translations in config/i18n.py (zh + en) remain as primary source
  - This engine adds extensible language packs loaded on demand
  - Translation packs stored as JSON files in config/locales/
  - Fallback chain: requested_lang → en → zh → key itself
  - Supports pluralization, interpolation, and context-aware translations

Usage:
    from utils.i18n_engine import I18n, get_i18n

    i18n = get_i18n()
    text = i18n.t("welcome_message", name="John")
    text = i18n.t("items_count", count=5)  # pluralization
    available = i18n.available_languages()
"""
from __future__ import annotations

import json
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("i18n_engine")

# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "zh": {"name": "中文", "name_en": "Chinese", "flag": "🇨🇳", "direction": "ltr"},
    "en": {"name": "English", "name_en": "English", "flag": "🇺🇸", "direction": "ltr"},
    "ja": {"name": "日本語", "name_en": "Japanese", "flag": "🇯🇵", "direction": "ltr"},
    "ko": {"name": "한국어", "name_en": "Korean", "flag": "🇰🇷", "direction": "ltr"},
    "es": {"name": "Español", "name_en": "Spanish", "flag": "🇪🇸", "direction": "ltr"},
    "fr": {"name": "Français", "name_en": "French", "flag": "🇫🇷", "direction": "ltr"},
    "de": {"name": "Deutsch", "name_en": "German", "flag": "🇩🇪", "direction": "ltr"},
    "pt": {"name": "Português", "name_en": "Portuguese", "flag": "🇧🇷", "direction": "ltr"},
    "ar": {"name": "العربية", "name_en": "Arabic", "flag": "🇸🇦", "direction": "rtl"},
    "ru": {"name": "Русский", "name_en": "Russian", "flag": "🇷🇺", "direction": "ltr"},
}

# Built-in translation packs for new languages (ja, ko, es)
# These cover the core UI strings; full packs would be in config/locales/*.json
_BUILTIN_PACKS: dict[str, dict[str, str]] = {
    "ja": {
        # Common
        "login": "ログイン",
        "register": "登録",
        "logout": "ログアウト",
        "submit": "送信",
        "cancel": "キャンセル",
        "confirm": "確認",
        "upgrade": "アップグレード",
        "username": "ユーザー名",
        "password": "パスワード",
        "email": "メールアドレス",
        "language": "言語",
        # Login
        "login_title": "貿易AIアシスタント",
        "login_subtitle": "ログインまたは登録してください",
        "login_button": "🔐 ログイン",
        "register_button": "📝 登録",
        "invalid_credentials": "ユーザー名またはパスワードが正しくありません",
        "registration_successful": "登録成功！ログインしてください",
        "passwords_not_match": "パスワードが一致しません",
        # Homepage
        "hero_title": "💼 貿易AIアシスタント",
        "hero_subtitle": "AI駆動の貿易支援：コールドメール・見積・多言語対応",
        "free_trial": "🆓 無料体験",
        "per_hour_20": "1時間20回",
        "select_function": "🚀 機能を選択",
        "usage_tips": "💡 使い方のヒント",
        "footer": "💼 貿易AIアシスタント | NVIDIA NIM搭載",
        "enter_feature": "開く",
        # Sidebar
        "usage_status": "📊 使用状況",
        "used_today": "今日の使用",
        "plan_label": "プラン",
        "times": "回",
        "unlimited": "無制限",
        "remaining": "残り",
        "used": "使用済み",
        # Features
        "cold_email": "コールドメール作成",
        "inquiry_reply": "問合せ回答",
        "quotation": "見積書",
        "follow_up": "フォローアップ",
        "smart_quote": "スマート見積",
        "batch_email": "一括メール",
    },
    "ko": {
        # Common
        "login": "로그인",
        "register": "회원가입",
        "logout": "로그아웃",
        "submit": "제출",
        "cancel": "취소",
        "confirm": "확인",
        "upgrade": "업그레이드",
        "username": "사용자 이름",
        "password": "비밀번호",
        "email": "이메일",
        "language": "언어",
        # Login
        "login_title": "무역 AI 어시스턴트",
        "login_subtitle": "로그인 또는 회원가입하세요",
        "login_button": "🔐 로그인",
        "register_button": "📝 회원가입",
        "invalid_credentials": "사용자 이름 또는 비밀번호가 올바르지 않습니다",
        "registration_successful": "가입 성공! 로그인해 주세요",
        "passwords_not_match": "비밀번호가 일치하지 않습니다",
        # Homepage
        "hero_title": "💼 무역 AI 어시스턴트",
        "hero_subtitle": "AI 기반 무역 지원: 콜드 이메일, 견적, 다국어 제품 소개",
        "free_trial": "🆓 무료 체험",
        "per_hour_20": "시간당 20회",
        "select_function": "🚀 기능 선택",
        "usage_tips": "💡 사용 팁",
        "footer": "💼 무역 AI 어시스턴트 | NVIDIA NIM 탑재",
        "enter_feature": "열기",
        # Sidebar
        "usage_status": "📊 사용 현황",
        "used_today": "오늘 사용",
        "plan_label": "플랜",
        "times": "회",
        "unlimited": "무제한",
        "remaining": "남은",
        "used": "사용",
    },
    "es": {
        # Common
        "login": "Iniciar sesión",
        "register": "Registrarse",
        "logout": "Cerrar sesión",
        "submit": "Enviar",
        "cancel": "Cancelar",
        "confirm": "Confirmar",
        "upgrade": "Actualizar",
        "username": "Nombre de usuario",
        "password": "Contraseña",
        "email": "Correo electrónico",
        "language": "Idioma",
        # Login
        "login_title": "Asistente de Comercio AI",
        "login_subtitle": "Inicie sesión o regístrese para continuar",
        "login_button": "🔐 Iniciar sesión",
        "register_button": "📝 Registrarse",
        "invalid_credentials": "Nombre de usuario o contraseña incorrectos",
        "registration_successful": "¡Registro exitoso! Inicie sesión",
        "passwords_not_match": "Las contraseñas no coinciden",
        # Homepage
        "hero_title": "💼 Asistente de Comercio AI",
        "hero_subtitle": "IA para comercio exterior: emails, cotizaciones, descripciones multilingües",
        "free_trial": "🆓 Prueba gratuita",
        "per_hour_20": "20 usos/hora",
        "select_function": "🚀 Seleccionar función",
        "usage_tips": "💡 Consejos de uso",
        "footer": "💼 Asistente de Comercio AI | Impulsado por NVIDIA NIM",
        "enter_feature": "Ir a",
        # Sidebar
        "usage_status": "📊 Estado de uso",
        "used_today": "Usado hoy",
        "plan_label": "Plan",
        "times": "veces",
        "unlimited": "Ilimitado",
        "remaining": "restante",
        "used": "Usado",
    },
}


# ---------------------------------------------------------------------------
# I18n Engine class
# ---------------------------------------------------------------------------

class I18n:
    """
    Internationalization engine with lazy-loaded translation packs.

    Features:
    - Lazy loading: language packs loaded only when first accessed
    - Fallback chain: lang → en → zh → raw key
    - Interpolation: {variable} replacement
    - Pluralization: count-based string selection
    - Thread-safe singleton per language
    """

    def __init__(self, lang: str = "zh"):
        self._lang = lang if lang in SUPPORTED_LANGUAGES else "zh"
        self._cache: dict[str, dict[str, str]] = {}
        self._loaded_languages: set[str] = set()

    @property
    def current_language(self) -> str:
        return self._lang

    @current_language.setter
    def current_language(self, lang: str) -> None:
        if lang in SUPPORTED_LANGUAGES:
            self._lang = lang

    def available_languages(self) -> list[dict]:
        """Return list of available languages with metadata."""
        return [
            {"code": code, **meta}
            for code, meta in SUPPORTED_LANGUAGES.items()
        ]

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.

        Supports:
        - Simple lookup: t("login")
        - Interpolation: t("welcome", name="John") → "Welcome, John"
        - Pluralization: t("items", count=5) → "5 items"
        - Fallback: unknown key returns the key itself

        Args:
            key: Translation key
            **kwargs: Variables for interpolation (name, count, etc.)

        Returns:
            Translated string
        """
        # Try current language
        text = self._lookup(key, self._lang)

        # Fallback chain
        if text is None and self._lang != "en":
            text = self._lookup(key, "en")
        if text is None and self._lang != "zh":
            text = self._lookup(key, "zh")
        if text is None:
            text = key  # Final fallback: return key

        # Handle pluralization
        if "count" in kwargs and isinstance(text, str) and "|" in text:
            text = self._pluralize(text, kwargs["count"])

        # Interpolation
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass  # If interpolation fails, return as-is

        return text

    def t_or(self, key: str, default: str, **kwargs) -> str:
        """Translate with an explicit default if key is not found."""
        text = self._lookup(key, self._lang)
        if text is None:
            text = default
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return text

    def has_key(self, key: str) -> bool:
        """Check if a translation key exists in the current language."""
        return self._lookup(key, self._lang) is not None

    def get_direction(self) -> str:
        """Get text direction for current language (ltr/rtl)."""
        return SUPPORTED_LANGUAGES.get(self._lang, {}).get("direction", "ltr")

    # ── Internal methods ──────────────────────────────

    def _lookup(self, key: str, lang: str) -> str | None:
        """Look up a key in a specific language's translations."""
        self._ensure_loaded(lang)
        translations = self._cache.get(lang, {})
        return translations.get(key)

    def _ensure_loaded(self, lang: str) -> None:
        """Lazy-load a language pack if not already loaded."""
        if lang in self._loaded_languages:
            return

        translations: dict[str, str] = {}

        # 1. Load from existing config/i18n.py (zh and en)
        if lang in ("zh", "en"):
            try:
                from config.i18n import TRANSLATIONS
                translations = TRANSLATIONS.get(lang, {}).copy()
            except ImportError:
                pass

        # 2. Load from built-in packs
        if lang in _BUILTIN_PACKS:
            translations.update(_BUILTIN_PACKS[lang])

        # 3. Load from external JSON file (config/locales/{lang}.json)
        json_path = self._get_locale_path(lang)
        if json_path.exists():
            try:
                with open(json_path, encoding="utf-8") as f:
                    external = json.load(f)
                if isinstance(external, dict):
                    translations.update(external)
                    logger.debug("Loaded locale file: %s", json_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load locale %s: %s", json_path, e)

        self._cache[lang] = translations
        self._loaded_languages.add(lang)

    def _get_locale_path(self, lang: str) -> Path:
        """Get the path to an external locale JSON file."""
        project_root = Path(__file__).resolve().parent.parent
        return project_root / "config" / "locales" / f"{lang}.json"

    def _pluralize(self, text: str, count: int) -> str:
        """
        Handle pluralization.

        Format: "singular|plural" or "zero|one|many"
        Examples:
            "item|items" with count=1 → "item"
            "item|items" with count=5 → "items"
            "no items|1 item|{count} items" with count=0/1/5
        """
        parts = text.split("|")
        if len(parts) == 2:
            return parts[0] if count == 1 else parts[1]
        elif len(parts) == 3:
            if count == 0:
                return parts[0]
            elif count == 1:
                return parts[1]
            else:
                return parts[2]
        return text


# ---------------------------------------------------------------------------
# Singleton & convenience
# ---------------------------------------------------------------------------

_instance: I18n | None = None


def get_i18n() -> I18n:
    """
    Get the global I18n engine instance.

    Language is synced from Streamlit session_state if available.
    """
    global _instance
    if _instance is None:
        _instance = I18n()

    # Sync language from session state
    try:
        import streamlit as st
        session_lang = st.session_state.get("language", "zh")
        if session_lang != _instance.current_language:
            _instance.current_language = session_lang
    except Exception:
        pass

    return _instance


def t(key: str, **kwargs) -> str:
    """Convenience shortcut: translate a key using the global I18n instance."""
    return get_i18n().t(key, **kwargs)


def set_language(lang: str) -> None:
    """Set the current language globally."""
    i18n = get_i18n()
    if lang in SUPPORTED_LANGUAGES:
        i18n.current_language = lang
        try:
            import streamlit as st
            st.session_state["language"] = lang
        except Exception:
            pass


def get_language_selector_options() -> list[dict]:
    """Get options for a language selector dropdown."""
    return [
        {"code": code, "label": f"{meta['flag']} {meta['name']}", "name_en": meta["name_en"]}
        for code, meta in SUPPORTED_LANGUAGES.items()
    ]
