"""
Future application entry point.

This will eventually orchestrate the full pipeline:

    Camera -> Vision -> Decision -> Guide Service -> UI -> Robot Controller

PHASE 1 STATUS: NOT IMPLEMENTED.

This phase only delivers the project architecture and a standalone,
independent Vision module. Full integration will be implemented once
Vision, Decision, Guide, Robot Controller, and UI are all complete.

To try the Vision module independently right now, run:

    python scripts/run_vision_demo.py
"""


def main() -> None:
    print(
        "AI University Lab Guide Robot — full application is not yet "
        "implemented.\n"
        "This is Phase 1: Architecture + Vision module only.\n"
        "Run the standalone Vision demo instead:\n"
        "    python scripts/run_vision_demo.py"
    )


if __name__ == "__main__":
    main()
