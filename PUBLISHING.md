# Publish the checkpoint history

In this local handoff, you can inspect the `main` branch and eleven annotated `checkpoint/*` tags with `git log --oneline --decorate --reverse`. Inspect any tag with `git show --stat checkpoint/chapter-03`.

The official release is free. The Night Nine contributors chose GNU GPL version 3 only for their original code. When you distribute a compiled release, keep the copyright, license and applicable third-party notices, and offer the matching complete corresponding source from the same download location at no extra charge. Include the source materials and scripts needed to modify and rebuild that version. Preserve any additional permissions for separately licensed components. [GPLv3](LICENSE) · [Media terms](MEDIA.md) · [Third-party notices](game/LICENSES.txt)

For the 0.7.0 desktop release, upload `NightNine-0.7.0-source.zip` beside the macOS and Windows downloads. You can also upload `NightNine-0.7.0-chapters.bundle` for readers who want the playable chapter history.

To publish the commits and annotated tags, create an empty GitHub repository, substitute its SSH URL below, and run these commands from this repository.

```sh
git remote add origin git@github.com:OWNER/REPOSITORY.git
git push --atomic --follow-tags -u origin main
```

If you already configured a remote, inspect it with `git remote -v` and use its verified name. For GitHub issue milestones, use Issues → Milestones and the titles and criteria in [MILESTONES.md](MILESTONES.md). You can also preview those entries locally with `python3 tools/create-github-milestones.py --repo OWNER/REPOSITORY`. To create missing entries in that repository, authenticate the GitHub CLI and rerun the command with `--apply`. You can rerun it after an interruption. The script skips existing open and closed milestones with matching titles.
