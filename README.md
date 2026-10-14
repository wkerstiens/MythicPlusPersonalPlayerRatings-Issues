# Mythic+ Personal Player Ratings: issues and feedback

Public issue tracker for **Mythic+ Personal Player Ratings** (MPPPR), a World of
Warcraft (Retail, Midnight) addon that keeps private, account-wide ratings and
notes for the players you run Mythic+ with, and shows them on tooltips and in the
Group Finder.

This repository holds no source code. It exists so bug reports and suggestions
have one place to live.

## Install

Get the addon from [CurseForge](https://www.curseforge.com/projects/1745387), or
unzip it into `World of Warcraft/_retail_/Interface/AddOns/` so the folder is
`AddOns/MythicPlusPersonalPlayerRatings`. Then reload the game.

## Using it

- `/mpppr` or `/ratings` opens the management window (also the minimap button).
- `/mpppr target` opens the editor for your current target.
- `/mpppr rate Name-Realm good|neutral|avoid` quick-rates from chat.
- `/mpppr export` / `/mpppr import` open the Share / Backup window.
- `/mpppr last` re-opens the rating popup for your most recent run.
- `/mpppr config` shows the options; `/mpppr toggle tooltips|lfgicons|popup|autotag|notify` flips one.

Things worth knowing:

- Ratings are stored account-wide and never broadcast. Sharing is a copyable
  export string you hand over yourself.
- Importing only fills blanks. It never overwrites a rating or note you made.
- Group Finder internals change between patches. If the icons stop appearing
  after a patch, say so in an issue; tooltips are unaffected.

## Posting an issue

1. [Search the existing issues](../../issues) first; yours may already be there.
2. [Open a new issue](../../issues/new/choose) and pick *Bug report* or *Suggestion*.
3. Include, as far as you can:
   - what you expected and what happened instead
   - the addon version (the AddOns list on the character-select screen)
   - any Lua error text (an addon such as BugSack makes these easy to copy)
   - a screenshot, if it is a display problem

Exports contain character names and your notes. Remove anything you would rather
not share.
