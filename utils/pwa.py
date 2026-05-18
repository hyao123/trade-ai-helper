"""
utils/pwa.py
------------
Progressive Web App (PWA) support for mobile installation.

Injects:
- Web App Manifest link
- Service Worker registration script
- iOS meta tags for standalone mode
- Theme color and viewport settings

Usage:
    from utils.pwa import inject_pwa_meta

    # Call once at app startup (e.g., in app.py or inject_css)
    inject_pwa_meta()
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def inject_pwa_meta() -> None:
    """
    Inject PWA meta tags and service worker registration into the page.

    Should be called once per page load (idempotent via session_state).
    Adds:
    - <link rel="manifest"> for installability
    - <meta> tags for iOS standalone mode
    - Service worker registration script
    - Viewport and theme-color meta tags
    """
    if st.session_state.get("_pwa_injected"):
        return

    # Inject manifest and meta tags via markdown
    st.markdown("""
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="theme-color" content="#3b82f6">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="TradeAI">
    <link rel="apple-touch-icon" href="/app/static/icon-192.png">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    """, unsafe_allow_html=True)

    # Register service worker via a tiny HTML component
    components.html("""
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/app/static/sw.js', { scope: '/' })
            .then(function(reg) {
                console.log('[PWA] Service Worker registered:', reg.scope);
            })
            .catch(function(err) {
                console.log('[PWA] SW registration failed:', err);
            });
    }
    </script>
    """, height=0)

    st.session_state["_pwa_injected"] = True


def show_install_prompt() -> None:
    """
    Show an install banner for users on mobile who haven't installed the PWA.

    Uses a dismissible info box with instructions.
    """
    if st.session_state.get("_pwa_install_dismissed"):
        return

    # Only show on mobile-like viewports (detected via component)
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.info(
                "📱 **添加到主屏幕** — 在浏览器菜单中选择「添加到主屏幕」，"
                "获得原生 App 体验（离线可用、全屏显示）"
            )
        with col2:
            if st.button("✕", key="_pwa_dismiss", help="不再显示"):
                st.session_state["_pwa_install_dismissed"] = True
                st.rerun()
