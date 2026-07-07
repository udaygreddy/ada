# Installing ADA (ADP Discovery Agent)

Step-by-step instructions to install and run ADA in your AI assistant. Pick the
section for your tool. Each has **macOS** and **Windows** steps.

ADA runs entirely in **your** environment — it reads your files and mailbox with
your permission and produces a package for you to send to ADP. Nothing is sent
anywhere automatically.

---

## What you were given

Depending on your tool, you'll use one of these (your ADP contact provides them):

| Tool | File you need |
|---|---|
| Claude Cowork (desktop app) | `ada-discovery.plugin` |
| Claude.ai (web chat) | `ada-discovery-skill.zip` |
| Claude Code (terminal) | the `ada-discovery` folder (or the zip) |
| GitHub Copilot (VS Code) | the `ada-discovery` folder |
| Claude Code / Copilot / Cursor / Codex **via apm** | nothing — installs from GitHub (see §0) |

> The `.zip`/folder and the `.plugin` contain the same skill — just packaged
> differently for each tool. **If you use a coding assistant, §0 (apm) is the
> quickest path** — one command, no files to download.

## One-time prerequisites

- **Python 3** must be installed (the skill uses small helper scripts).
  - **macOS:** usually already installed. Check: open **Terminal** and run
    `python3 --version`. If missing, install from <https://www.python.org/downloads/>.
  - **Windows:** install from <https://www.python.org/downloads/> and **tick
    "Add python.exe to PATH"** during setup. Check in **PowerShell**:
    `python --version`.
- A **mailbox connector** (Gmail or Outlook) so ADA can find the ADP request
  email. Optionally a **QuickBooks** connector if ADP asked for accounting data.
  (How to connect these is in each section below.)

---

## 0) Install with apm — Claude Code, Copilot, Cursor, Codex, and more

[apm](https://microsoft.github.io/apm/) (Agent Package Manager) installs ADA into
your project and wires it into whichever coding assistant you use — **one command,
no files to download**. Best if you work in a code editor / terminal.

### macOS & Windows

1. Install the apm CLI (once):
   - **macOS/Linux:** `pip install apm-cli`  *(or `brew`/native binary)*
   - **Windows:** `pip install apm-cli`  *(or `scoop install apm`)*
2. From the folder/project you'll work in, install ADA for your assistant:
   ```sh
   apm install udaygreddy/ada --target claude     # Claude Code
   # or:  --target copilot   |   --target cursor   |   --target codex
   ```
   apm places the skill in the right spot for that tool automatically.
3. Connect your **mailbox** (Gmail/Outlook) and optionally **QuickBooks** as MCP
   servers in that tool (see the per-tool sections below for how), and make sure
   **Python 3** is installed (see prerequisites above).
4. In your assistant, type:
   > *ADP asked us for documents — help me gather everything they requested.*

> Don't have apm and prefer a manual install? Use the per-tool sections below.

---

## 1) Claude Cowork (desktop app) — easiest

### macOS & Windows (same steps)

1. Open the **Claude** desktop app.
2. Drag the **`ada-discovery.plugin`** file into the chat window and drop it.
   - *Alternative:* open **Settings → Plugins → Install from file** and select
     `ada-discovery.plugin`.
3. When the install card appears, click **Install / Accept**.
4. Connect your mailbox: **Settings → Connectors → Add** → choose **Gmail** (or
   Outlook) and sign in. *(Optional: also add **QuickBooks**.)*
5. Start a new chat and type:
   > *ADP asked us for documents — help me gather everything they requested.*

That's it. ADA will greet you and begin.

---

## 2) Claude.ai (web chat at claude.ai)

> **Requires** a paid plan (Pro, Max, Team, or Enterprise) with **code execution
> / Analysis tool enabled**. Skills are per-user (not shared org-wide).
>
> **Important:** claude.ai runs in the cloud, so it **cannot read files on your
> computer**. When ADA asks for exported reports (e.g. from Paychex/Paylocity),
> you'll **upload** those files into the chat instead of pointing to a folder.

### macOS & Windows (same steps — it's a website)

1. Go to **claude.ai** and sign in.
2. Click your name → **Settings → Features** (also called *Capabilities*).
3. Turn on **Code execution / Analysis tool** if it isn't already.
4. Find **Skills** → **Upload skill** → select **`ada-discovery-skill.zip`**.
5. Add your mailbox: **Settings → Connectors** → **Gmail** (or Outlook) → sign in.
   *(Optional: add **QuickBooks**.)*
6. Start a new chat and type:
   > *ADP asked us for documents — help me gather everything they requested.*

---

## 3) Claude Code (terminal / CLI)

You install the skill by placing its folder in your Claude skills directory.

### macOS

1. Open **Terminal**.
2. Make the skills folder and copy ADA in (adjust the source path to wherever you
   saved it):
   ```sh
   mkdir -p ~/.claude/skills
   cp -R ~/Downloads/ada-discovery ~/.claude/skills/ada-discovery
   ```
   *(If you were given the zip instead: `unzip ~/Downloads/ada-discovery-skill.zip -d ~/.claude/skills/`)*
3. Connect your mailbox as an MCP server (example for a Gmail MCP):
   ```sh
   claude mcp add gmail            # follow the prompts to authorize
   ```
4. In Claude Code, run `/reload-plugins` (or restart), then type:
   > *ADP asked us for documents — help me gather everything they requested.*

### Windows (PowerShell)

1. Open **PowerShell**.
2. Create the folder and copy ADA in:
   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
   Copy-Item -Recurse "$env:USERPROFILE\Downloads\ada-discovery" "$env:USERPROFILE\.claude\skills\ada-discovery"
   ```
   *(From the zip: `Expand-Archive "$env:USERPROFILE\Downloads\ada-discovery-skill.zip" "$env:USERPROFILE\.claude\skills\"`)*
3. Connect your mailbox: `claude mcp add gmail` and follow the prompts.
4. Run `/reload-plugins` (or restart Claude Code), then type the same request as above.

> **Tip:** you can also install via the marketplace: type `/plugin` in Claude
> Code, open **Discover**, and install if ADA has been published to a marketplace
> you've added.

---

## 4) GitHub Copilot (VS Code)

Copilot doesn't install the plugin; it reads the skill's instructions from a
folder in your project and connects to tools via MCP.

### macOS & Windows (same steps in VS Code)

1. Put the **`ada-discovery`** folder inside the project/repo you'll work in
   (e.g. a new empty folder you open in VS Code).
2. Open that folder in **VS Code**. Ensure **GitHub Copilot** and **Copilot Chat**
   extensions are installed and you're signed in.
3. In Copilot Chat, switch to **Agent** mode (the mode dropdown at the top of the
   chat panel).
4. Point Copilot at the instructions: the folder already contains **`AGENTS.md`**.
   Copilot reads it automatically. *(Optional: copy `ada-discovery/AGENTS.md` to
   `.github/copilot-instructions.md` at the repo root for stronger pickup.)*
5. Connect your mailbox (and QuickBooks) via MCP. Create **`.vscode/mcp.json`** in
   the project:
   ```json
   {
     "servers": {
       "gmail": { "command": "npx", "args": ["-y", "<your-gmail-mcp-server>"] }
     }
   }
   ```
   *(Or use the command palette: **MCP: Add Server**. Your ADP contact can tell
   you the exact server to use.)*
6. In Copilot Chat (Agent mode), type:
   > *ADP asked us for documents — help me gather everything they requested. Follow AGENTS.md.*

> **Windows note:** the helper scripts are invoked as `python3`. If Copilot reports
> *"python3 not found"*, either install Python via the Microsoft Store (which
> provides a `python3` alias) or tell Copilot to use `python` instead.

---

## Verify it's working

In any tool, after install, type:

> *ADP asked us for documents — help me gather everything they requested.*

ADA should:
1. Greet you and ask permission to look at your mailbox.
2. Find the ADP request email and list the documents ADP asked for.
3. Walk you through exporting them from your payroll system (Paychex/Paylocity)
   and/or reading QuickBooks.
4. Produce an **`ada_package`** folder for you to send to ADP.

## Troubleshooting

- **Nothing happens when I type the request** → make sure the skill is installed
  and enabled, and (Claude Code) that you ran `/reload-plugins` or restarted.
- **"python3 not found" (Windows)** → install Python 3 with "Add to PATH" ticked,
  or install from the Microsoft Store. Restart the app afterward.
- **ADA can't see the ADP email** → confirm your **Gmail/Outlook connector** is
  added and authorized in your tool's settings.
- **claude.ai can't open my files** → that's expected; claude.ai is cloud-based.
  **Upload** the exported reports into the chat when ADA asks.
- **Still stuck** → contact your ADP implementation representative.
