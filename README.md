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

### The window

`/mpppr` or `/ratings` (or the minimap button, or the AddOn Compartment button
next to the minimap) opens the window. It has three tabs, and always opens on the
first:

- **Ratings**: the Good / Neutral / Avoid / Unrated sections with live counts. Search
  matches names, people, notes and tags. Click a column header (Character, Runs,
  Last seen) to sort, and again to reverse. Click a row to edit it; the red X
  deletes it (two clicks).
- **Clean up data**: remove characters by rating and by days since last seen, with
  a live count and a two-click confirm; set how many days before unrated players
  are purged automatically; and undo the last cleanup or the last automatic purge.
- **Config**: switch features on and off (tooltips, Group Finder icons and
  highlights, the rate-your-group popup, the right-click entry, auto-linking
  Battle.net friends, join announcements, the Avoid sound and screen alert, the
  minimap button), edit the auto-avoid realms, and open Share / Backup.

### Rating someone

- In the editor: a flag (Good / Neutral / Avoid; click the selected one to clear
  it), tags, a note, and a link to a person.
- Right-click a player (unit frame, party, raid, target, or a Group Finder entry or
  applicant) and use **M+ Ratings**.
- After a key, the rate-your-group popup lists everyone you ran with.
- From chat: `/mpppr rate Name-Realm good|neutral|avoid`, or `/mpppr target` to edit
  your current target.

### Commands

| Command | What it does |
|---|---|
| `/mpppr` or `/ratings` | Open the window |
| `/mpppr settings` | Open the Config tab |
| `/mpppr target` | Edit your current target |
| `/mpppr rate Name-Realm flag` | Rate from chat |
| `/mpppr export` / `/mpppr import` | Open Share / Backup |
| `/mpppr last` | Re-open the rating popup for your most recent run |
| `/mpppr undo [cleanup\|purge]` | Restore the last cleanup or automatic purge |
| `/mpppr config` | Print the current options |
| `/mpppr toggle tooltips\|lfgicons\|lfghighlight\|popup\|autotag\|notify\|minimap` | Flip a feature |

Things worth knowing:

- Ratings are stored account-wide and never broadcast. Sharing is a copyable
  export string you hand over yourself, and importing only fills blanks: it never
  overwrites a rating, note or tag you made.
- Players with no flag, note, tag or person link are removed once you have not
  grouped with them for a number of days (7 by default; 0 turns it off). Days away
  from the game count, and nothing is purged until a full window after you first
  load the addon. Anything you rate, note, tag or link is kept.
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
