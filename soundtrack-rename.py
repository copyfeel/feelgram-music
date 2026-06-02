#!/usr/bin/env python3
"""
Rename music/soundtrack/ files to simple slugs (soundtrack-01.mp4, etc.)
so GitHub Releases (which sanitizes asset names) can host them safely,
and rewrite soundtrack.json to keep the original Korean title for UI use.

Sorting follows the same rule the app uses: Korean first (Hangul), then
the rest, localeCompare within each group.

Usage:
    python3 soundtrack-rename.py --dry-run   # show plan only
    python3 soundtrack-rename.py              # perform rename + write json
"""
import json, os, re, sys

SOUNDTRACK_DIR = 'music/soundtrack'
JSON_OUT = 'soundtrack.json'
VIDEO_EXTS = ('.mp4', '.mov', '.m4v', '.webm')
POSTER_EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def hangul_first(name: str) -> int:
    stripped = re.sub(r'^\[영화\]\s*', '', name).strip()
    ch = stripped[:1]
    return 0 if '가' <= ch <= '힣' else 1


def sort_key(name: str):
    stripped = re.sub(r'^\[영화\]\s*', '', name).strip()
    return (hangul_first(name), stripped)


def main():
    dry_run = '--dry-run' in sys.argv

    if not os.path.isdir(SOUNDTRACK_DIR):
        print(f'No such directory: {SOUNDTRACK_DIR}')
        sys.exit(1)

    all_files = os.listdir(SOUNDTRACK_DIR)
    videos = sorted([f for f in all_files if f.lower().endswith(VIDEO_EXTS)], key=sort_key)
    if not videos:
        print('No video files found.')
        sys.exit(1)

    plan = []
    for i, vfile in enumerate(videos, start=1):
        base, vext = os.path.splitext(vfile)
        # Skip if already in slug form
        if re.match(r'^soundtrack-\d{2}$', base):
            slug = base
        else:
            slug = f'soundtrack-{i:02d}'
        # Locate matching poster
        poster = None
        for p_ext in POSTER_EXTS:
            candidate = base + p_ext
            if candidate in all_files:
                poster = candidate
                break
        # Build target names (lower-case extension)
        target_video = f'{slug}{vext.lower()}'
        target_poster = f'{slug}{os.path.splitext(poster)[1].lower()}' if poster else None

        plan.append({
            'title': base,
            'video_from': vfile,
            'video_to': target_video,
            'poster_from': poster,
            'poster_to': target_poster,
        })

    # Print plan
    print(f'\n📦 Rename plan ({len(plan)} items) — Hangul first, then ASCII:')
    print('=' * 78)
    for item in plan:
        print(f"  {item['video_from']}")
        print(f"     → {item['video_to']}")
        if item['poster_from']:
            print(f"     poster: {item['poster_from']} → {item['poster_to']}")
        else:
            print(f"     poster: (none)")
    print('=' * 78)

    if dry_run:
        print('\nDry-run only. Re-run without --dry-run to apply.')
        return

    # Apply rename — two-pass to avoid clash if any source already happens
    # to look like a target slug.
    tmp_suffix = '.__tmprn__'
    for item in plan:
        for src_key, dst_key in (('video_from', 'video_to'), ('poster_from', 'poster_to')):
            src = item.get(src_key)
            dst = item.get(dst_key)
            if not src or not dst or src == dst:
                continue
            os.rename(
                os.path.join(SOUNDTRACK_DIR, src),
                os.path.join(SOUNDTRACK_DIR, src + tmp_suffix),
            )
    for item in plan:
        for src_key, dst_key in (('video_from', 'video_to'), ('poster_from', 'poster_to')):
            src = item.get(src_key)
            dst = item.get(dst_key)
            if not src or not dst:
                continue
            tmp = src + tmp_suffix
            if src == dst:
                continue
            tmp_path = os.path.join(SOUNDTRACK_DIR, tmp)
            if os.path.exists(tmp_path):
                os.rename(tmp_path, os.path.join(SOUNDTRACK_DIR, dst))

    # Write JSON keyed by the slug, with the original title for the UI.
    out = []
    for item in plan:
        entry = {
            'title': item['title'],
            'video': item['video_to'],
        }
        if item['poster_to']:
            entry['poster'] = item['poster_to']
        out.append(entry)

    with open(JSON_OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n✅ Rename complete. {JSON_OUT} updated with {len(out)} entries.')
    print(f'Next: upload music/soundtrack/* to GitHub Release as assets.')


if __name__ == '__main__':
    main()
