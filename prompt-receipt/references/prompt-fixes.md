# Prompt fixes: keywords and templates

Use these to build the "keywords to add" and rewrites in the review. Replace the placeholders with the user's real names from the chat (files, routes, components). Generic words help far less than the project's own words.

## Keywords that save the most tokens

| What was missing | Words to add | Why it helps |
|---|---|---|
| Where | file path, component or function name, route (`POST /api/predict`), page URL | Claude reads that file instead of searching the project |
| What happened | exact error text, status code (`500`), terminal output, screenshot | Diagnosis instead of guessing |
| What you did | "after I click X / run Y / upload Z" | Reproduces the bug in one try |
| What you expected | "should return...", "expected: ...", "instead of ..." | Defines done, so no back-and-forth |
| Boundaries | "only change X", "don't touch Y", "keep the existing API" | Stops side-edits you then have to undo |
| Environment | OS, Python/Node version, "running on localhost:5000", "venv active" | Avoids wrong-setup answers |
| Order | "first backend, then test with curl, then frontend" | One goal per message |
| Verification | "run it and show me the output", "add a test for it" | Claude proves the fix |

## Templates

**Bug fix**

    In <file or page>, <what I did> gives <what happens>. Expected: <what should happen>.
    Error:
    <paste exact error / log>
    Only change <scope>. Run it and show the result.

**Backend endpoint** (example: image upload for disease prediction)

    Add POST /api/predict in <backend/file.py>. Input: multipart image (jpg/png, max 5 MB).
    Load the model from <path>, return JSON {"disease": str, "confidence": float, "treatment": str}.
    Errors: 400 for a bad file, 500 with a message if the model fails to load.
    Test it with curl and show the response.

**Frontend page**

    Build <PageName> in <frontend/path>. Sections: <list>. It calls <endpoint> and shows <fields>.
    States: loading, error, empty. Responsive down to 375px. Reuse <existing component / style file>.

**Connect frontend to backend**

    The <component> should call <METHOD /route> on <base URL>, send <payload>, and render <response field>.
    Right now the browser console shows: <paste>. Keep the existing UI.

**ML model integration**

    Use <model file> with <framework>. Input: <size / preprocessing>. Output classes: <where listed>.
    Write a function predict(image_path) in <file>. Test on <sample image> and print the top 3 classes.

**New feature request**

    Add <feature>. User flow: 1) ... 2) ... 3) .... Done means <observable result>.
    Touch only <files/areas>. Ask me before adding new dependencies.

**Starting a fresh chat for the next phase**

    Project: <name>, stack <...>. Done: <list>. Pending: <list>. Decisions: <list>.
    Run backend: <cmd>. Run frontend: <cmd>. Task now: <one goal>.

## Habits worth naming

- One goal per message; finish and check it before the next.
- Paste the error, do not describe it.
- Start a new chat when the topic changes (backend work done, frontend begins).
- Put run commands and conventions in `CLAUDE.md` once.
- Use plan mode for big builds: agree the plan, then implement.
- Ask quick questions in a short fresh chat, not at the end of a 900k-token one.
