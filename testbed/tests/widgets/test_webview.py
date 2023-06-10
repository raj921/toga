import asyncio
from asyncio import wait_for
from contextlib import nullcontext
from unittest.mock import ANY, Mock

import pytest

import toga
from toga.style import Pack

from .properties import (  # noqa: F401
    test_flex_widget_size,
    test_focus,
)

LOAD_TIMEOUT = 2
JS_TIMEOUT = 0.5


async def get_content(widget, timeout):
    return await wait_for(
        widget.evaluate_javascript("document.body.innerHTML"),
        timeout,
    )


async def assert_content_change(widget, probe, message, url, content, on_load):
    # Web views aren't instantaneous. Even for simple static changes of page
    # content, the DOM won't be immediately rendered. As a result, even though a
    # page loaded signal has been received, it doesn't mean the accessors for
    # the page URL or DOM content has been updated in the widget. This is a
    # problem for tests, as we need to "make change, test change occurred" with
    # as little delay as possible. So - wait for up to 2 seconds for the URL
    # *and* content to change in any way before asserting the new values.

    changed = False
    timer = LOAD_TIMEOUT

    await probe.redraw(message)

    # Loop until a change occurs
    while timer > 0 and not changed:
        new_url = widget.url
        new_content = await get_content(widget, timer)

        changed = new_url == url and new_content == content
        if not changed:
            timer -= 0.05
            await asyncio.sleep(0.05)

    if not changed:
        pytest.fail(f"{new_url=!r}, {url=!r}, {new_content[:50]=!r}, {content=!r}")

    if not probe.supports_on_load:
        on_load.assert_not_called()
    else:
        # Loop until an event occurs
        while timer > 0 and not on_load.mock_calls:
            timer -= 0.05
            await asyncio.sleep(0.05)
        on_load.assert_called_with(widget)


@pytest.fixture
async def widget():
    widget = toga.WebView(style=Pack(flex=1))

    # Set some initial content that has a visible background
    widget.set_content(
        "https://example.com/",
        "<html style='background-color:rebeccapurple;'></html>",
    )
    return widget


@pytest.fixture
async def on_load(widget):
    on_load = Mock()
    widget.on_webview_load = on_load
    return on_load


async def test_set_url(widget, probe, on_load):
    "The URL can be set"
    widget.url = "https://github.com/beeware"

    # Wait for the content to be loaded
    await assert_content_change(
        widget,
        probe,
        message="Page has been loaded",
        url="https://github.com/beeware",
        content=ANY,
        on_load=on_load,
    )


async def test_clear_url(widget, probe, on_load):
    "The URL can be cleared"
    widget.url = None

    # Wait for the content to be cleared
    await assert_content_change(
        widget,
        probe,
        message="Page has been cleared",
        url=None,
        content="",
        on_load=on_load,
    )


async def test_load_url(widget, probe, on_load):
    "A URL can be loaded into the view"
    await wait_for(
        widget.load_url("https://github.com/beeware"),
        LOAD_TIMEOUT,
    )

    # DOM loads aren't instantaneous; wait for the URL to appear
    await assert_content_change(
        widget,
        probe,
        message="Page has been loaded",
        url="https://github.com/beeware",
        content=ANY,
        on_load=on_load,
    )


async def test_static_content(widget, probe, on_load):
    "Static content can be loaded into the page"
    widget.set_content("https://example.com/", "<h1>Nice page</h1>")

    # DOM loads aren't instantaneous; wait for the URL to appear
    await assert_content_change(
        widget,
        probe,
        message="Webview has static content",
        url="https://example.com/" if probe.content_supports_url else None,
        content="<h1>Nice page</h1>",
        on_load=on_load,
    )


async def test_user_agent(widget, probe):
    "The user agent can be customized"

    # Default user agents are a mess, but they all start with "Mozilla/5.0"
    assert widget.user_agent.startswith("Mozilla/5.0 (")

    # Set a custom user agent
    widget.user_agent = "NCSA_Mosaic/1.0"
    await probe.redraw("User agent has been customized")
    assert widget.user_agent == "NCSA_Mosaic/1.0"


async def test_evaluate_javascript(widget, probe):
    "JavaScript can be evaluated"
    on_result_handler = Mock()

    for expression, expected in [
        ("37 + 42", 79),
        ("'awesome'.includes('we')", True),
        ("'hello js'", "hello js"),
    ]:
        # reset the mock for each pass
        on_result_handler.reset_mock()

        result = await wait_for(
            widget.evaluate_javascript(expression, on_result=on_result_handler),
            JS_TIMEOUT,
        )

        # The resulting value has been converted into Python
        assert result == expected
        # The same value was passed to the on-result handler
        on_result_handler.assert_called_once_with(expected)


async def test_evaluate_javascript_no_handler(widget, probe):
    "A handler isn't needed to evaluate JavaScript"
    result = await wait_for(
        widget.evaluate_javascript("37 + 42"),
        JS_TIMEOUT,
    )

    # The resulting value has been converted into Python
    assert result == 79


def javascript_error_context(probe):
    if probe.javascript_supports_exception:
        return pytest.raises(RuntimeError)
    else:
        return nullcontext()


async def test_evaluate_javascript_error(widget, probe):
    "If JavaScript content raises an error, the error is propegated"
    on_result_handler = Mock()

    with javascript_error_context(probe):
        result = await wait_for(
            widget.evaluate_javascript("not valid js", on_result=on_result_handler),
            JS_TIMEOUT,
        )
        # If the backend supports exceptions, the previous line should have raised one.
        assert not probe.javascript_supports_exception
        assert result is None

    # The same value was passed to the on-result handler
    on_result_handler.assert_called_once()
    assert on_result_handler.call_args.args == (None,)
    kwargs = on_result_handler.call_args.kwargs
    if probe.javascript_supports_exception:
        assert sorted(kwargs) == ["exception"]
        assert isinstance(kwargs["exception"], RuntimeError)
    else:
        assert kwargs == {}


async def test_evaluate_javascript_error_without_handler(widget, probe):
    "A handler isn't needed to propegate a JavaScript error"
    with javascript_error_context(probe):
        result = await wait_for(
            widget.evaluate_javascript("not valid js"),
            JS_TIMEOUT,
        )
        # If the backend supports exceptions, the previous line should have raised one.
        assert not probe.javascript_supports_exception
        assert result is None
