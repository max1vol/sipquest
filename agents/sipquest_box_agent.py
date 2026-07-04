from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):
        return False

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sipquest.box_controller import confirm_pickup, dispense_bottle
from sipquest.camera_vision import inspect_box
from sipquest.state import bool_env
from sipquest.intent import parse_drink_request
from sipquest.inventory import choose_bottle, format_inventory, is_ambiguous_request, load_inventory
from sipquest.reveal import format_reveal_response, generate_reveal


CLARIFICATION = "What quest direction do you want: chill, energy, wildcard, blue, or clear?"


def _visible_text(values: list[str]) -> str:
    if not values:
        return "camera inconclusive"
    names = {"blue": "blue bottle", "clear": "clear bottle"}
    return ", ".join(names.get(value, value) for value in values)


def _mentions_allergy_constraint(text: str) -> bool:
    normalized = text.lower()
    allergy_terms = [
        "allergy",
        "allergic",
        "allergen",
        "peanut",
        "nut",
        "tree nut",
        "dairy",
        "milk",
        "soy",
        "gluten",
        "wheat",
        "sesame",
    ]
    return any(term in normalized for term in allergy_terms)


def run_sipquest_workflow(text: str) -> str:
    request = parse_drink_request(text)
    inventory = load_inventory()

    if _mentions_allergy_constraint(request.raw_text):
        return (
            "I cannot guarantee allergy safety for the current two-bottle box, so I will not dispense based on allergy terms.\n"
            "I can safely handle the caffeine-free constraint, or you can ask for chill, energy, wildcard, blue, or clear."
        )

    if request.wants_inventory:
        camera_result = inspect_box()
        return (
            f"{format_inventory(inventory)}\n\n"
            f"Camera inspection: {_visible_text(camera_result.visible_bottles)} "
            f"({camera_result.source}, confidence {camera_result.confidence})."
        )

    if is_ambiguous_request(request):
        return CLARIFICATION

    print("SipQuest agent: inspecting the box camera...", flush=True)
    camera_result = inspect_box()
    print(f"SipQuest camera: saw {_visible_text(camera_result.visible_bottles)} via {camera_result.source}.", flush=True)

    selection = choose_bottle(request, inventory, camera_result)
    if not selection.slot:
        return f"I could not safely dispense a bottle. {selection.reason}"

    print(f"SipQuest selector: {selection.reason}", flush=True)
    dispense = dispense_bottle(selection.slot.slot_id, selection.slot)
    if not dispense.success:
        return (
            f"I selected {selection.slot.display_name}, but the box did not dispense.\n"
            f"Reason: {dispense.error or dispense.message}"
        )

    pickup = confirm_pickup(selection.slot.slot_id)
    reveal = generate_reveal(selection.slot, request, camera_result, dispense, pickup, selection)
    return format_reveal_response(reveal, selection, dispense, pickup)


def _create_text_chat(text: str):
    from uagents_core.contrib.protocols.chat import TextContent, ChatMessage

    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )


def run_agent() -> None:
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        StartSessionContent,
        TextContent,
        chat_protocol_spec,
    )

    agent_kwargs: dict[str, object] = {
        "name": os.getenv("AGENT_NAME", "sipquest-box-agent"),
        "port": int(os.getenv("AGENT_PORT", "8000")),
    }
    seed = os.getenv("AGENT_SEED", "").strip()
    if seed:
        agent_kwargs["seed"] = seed
    endpoint = os.getenv("AGENT_ENDPOINT", "").strip()
    if endpoint:
        agent_kwargs["endpoint"] = [endpoint]
    if bool_env("AGENT_MAILBOX", True):
        agent_kwargs["mailbox"] = True

    agent = Agent(**agent_kwargs)
    chat_proto = Protocol(spec=chat_protocol_spec)

    @agent.on_event("startup")
    async def startup(ctx: Context):
        ctx.logger.info("SipQuest Box Agent is running.")
        ctx.logger.info("Agent address: %s", ctx.agent.address)

    @chat_proto.on_message(ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        await ctx.send(
            sender,
            ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
        )

        text_parts: list[str] = []
        saw_start = False
        saw_end = False
        for item in msg.content:
            if isinstance(item, StartSessionContent):
                saw_start = True
            elif isinstance(item, EndSessionContent):
                saw_end = True
            elif isinstance(item, TextContent):
                text_parts.append(item.text)

        if saw_end and not text_parts:
            await ctx.send(sender, _create_text_chat("SipQuest session closed."))
            return

        user_text = " ".join(part.strip() for part in text_parts if part.strip())
        if saw_start and not user_text:
            await ctx.send(
                sender,
                _create_text_chat("SipQuest Box Agent is ready. Ask for chill, energy, wildcard, blue, or clear."),
            )
            return

        if not user_text:
            await ctx.send(sender, _create_text_chat(CLARIFICATION))
            return

        ctx.logger.info("SipQuest request from %s: %s", sender, user_text)
        try:
            response = run_sipquest_workflow(user_text)
        except Exception as exc:
            ctx.logger.exception("SipQuest workflow failed")
            response = f"SipQuest hit a runtime error and did not dispense. Safe message: {exc.__class__.__name__}."
        await ctx.send(sender, _create_text_chat(response))

    @chat_proto.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        ctx.logger.info("Chat acknowledgement from %s for %s", sender, msg.acknowledged_msg_id)

    agent.include(chat_proto, publish_manifest=True)
    agent.run()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="SipQuest Box Agent")
    parser.add_argument(
        "--local",
        nargs="*",
        help="Run one local workflow turn instead of starting the uAgent.",
    )
    args = parser.parse_args()

    if args.local is not None:
        text = " ".join(args.local).strip() or "I want a mystery drink, caffeine-free."
        print(run_sipquest_workflow(text))
        return

    run_agent()


if __name__ == "__main__":
    main()
