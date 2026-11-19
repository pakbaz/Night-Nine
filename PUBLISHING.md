# Publish the checkpoint history

In this local handoff, use `git log --oneline --decorate --reverse` to inspect the `main` branch, the eleven annotated `checkpoint/*` tags and subsequent releases. Inspect one chapter with `git show --stat checkpoint/chapter-03`.

The official release is free. The Night Nine contributors chose GNU GPL version 3 only for their original code. When you distribute a compiled release, keep the copyright, license and applicable third-party notices, and offer the matching complete corresponding source from the same download location at no extra charge. Include the source materials and scripts needed to modify and rebuild that version. Preserve any additional permissions for separately licensed components. [GPLv3](LICENSE) · [Media terms](MEDIA.md) · [Third-party notices](game/LICENSES.txt)

For v0.8.0, publish `NightNine-0.8.0-source.zip` beside `NightNine-0.8.0-Windows-x64.zip` and `NightNine-0.8.0-macOS.zip`. Attach `NightNine-0.8.0-chapters.bundle` for readers who want an offline copy of the Git history. Readers can use `git clone NightNine-0.8.0-chapters.bundle Night-Nine` to open it. Keep the 0.7.0 source available with the older desktop downloads.

## Browser play

After pushing the complete release to GitHub, create a GitHub Release for the tag `v0.8.0`. Attach the desktop downloads and `NightNine-0.8.0-source.zip` under that exact filename. Players can then choose **Full source and art masters** on the Pages site or open **Releases → v0.8.0** on the project page. That archive includes the editable painting, animation and audio masters. Players can download the smaller playable Godot checkout separately from the Pages site.

Select **Settings → Pages → Build and deployment → GitHub Actions**. Open **Actions → Publish Night Nine to GitHub Pages → Run workflow**, select the release tag or matching release branch and confirm. You can follow the deployment link from that run. Publishing requires someone with repository write access to start the workflow.

For local browser play, install Godot 4.7.2 with matching Web export templates, then run the following from the complete public repository. Place `NightNine-0.8.0-source.zip` in `builds/` for visitors who want the editable masters. Open `http://localhost:8000/web/`. The build uses the current Git commit and includes the corresponding playable checkout for download. Use a new output folder when rebuilding. You may supply the official Web release template directly with `--template /path/to/web_nothreads_release.zip`, or set a different masters download with `--source-url URL`.

```sh
python3 tools/build-pages.py --output builds/web
python3 -m http.server 8000 --bind 127.0.0.1 --directory builds
```

To publish the commits and annotated tags, create an empty GitHub repository, substitute its SSH URL below, and run these commands from this repository.

```sh
git remote add origin git@github.com:OWNER/REPOSITORY.git
git push --atomic --follow-tags -u origin main
```

If you already configured a remote, inspect it with `git remote -v` and use its verified name. For GitHub issue milestones, use Issues → Milestones and the titles and criteria in [MILESTONES.md](MILESTONES.md). You can also preview those entries locally with `python3 tools/create-github-milestones.py --repo OWNER/REPOSITORY`. To create missing entries in that repository, authenticate the GitHub CLI and rerun the command with `--apply`. You can rerun it after an interruption. The script skips existing open and closed milestones with matching titles.
