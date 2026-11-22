"""Turn a repainted variant of a room plate into a transparent story layer.

The image model repaints the whole scene and shifts the layout slightly, so a raw
replacement would move every clickable object. This aligns the generated painting to
the original plate by feature matching (a homography fitted outside the changed
regions), colour-matches it at the seams, and keeps only soft-edged regions (for
example the scan chair with Steve in it). It writes:
  --layer   an RGBA image the size of the plate, transparent outside the regions;
            the game paints it over the room while the story calls for it
  --preview the plate with the layer applied, for review

Usage:
  python graft_region.py ORIGINAL GENERATED --region x0 y0 x1 y1 [--region ...]
                         [--feather 0.03] --layer OUT.png [--preview OUT.png]
Region coordinates are fractions of the original plate.
"""
import argparse

import cv2
import numpy as np


def align(original, generated, regions):
    h, w = original.shape[:2]
    gen = cv2.resize(generated, (w, int(round(generated.shape[0] * w / generated.shape[1]))))
    sift = cv2.SIFT_create(nfeatures=8000)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(original, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(gen, cv2.COLOR_BGR2GRAY), None)
    pairs = cv2.BFMatcher().knnMatch(d2, d1, k=2)
    good = [m for m, n in pairs if m.distance < 0.72 * n.distance]

    def outside(point):
        return not any(x0 * w <= point[0] <= x1 * w and y0 * h <= point[1] <= y1 * h
                       for x0, y0, x1, y1 in regions)

    good = [m for m in good if outside(k1[m.trainIdx].pt)]
    if len(good) < 40:
        raise SystemExit(f"Only {len(good)} matches outside the regions; the repaint moved too much.")
    src = np.float32([k2[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    kept = inliers.ravel().astype(bool)
    moved = cv2.perspectiveTransform(src[kept], matrix).reshape(-1, 2)
    residual = float(np.median(np.linalg.norm(moved - dst[kept].reshape(-1, 2), axis=1)))
    warped = cv2.warpPerspective(gen, matrix, (w, h), flags=cv2.INTER_LANCZOS4)
    # Where the repaint does not reach (its edges after alignment), keep the original.
    covered = cv2.warpPerspective(np.full(gen.shape[:2], 255, np.uint8), matrix, (w, h), flags=cv2.INTER_NEAREST)
    covered = cv2.erode(covered, np.ones((7, 7), np.uint8))
    return warped, covered.astype(np.float32) / 255.0, int(kept.sum()), len(good), residual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original")
    parser.add_argument("generated")
    parser.add_argument("--region", nargs=4, type=float, action="append", required=True)
    parser.add_argument("--feather", type=float, default=0.03)
    parser.add_argument("--layer", required=True)
    parser.add_argument("--preview")
    args = parser.parse_args()
    original = cv2.imread(args.original, cv2.IMREAD_COLOR)
    generated = cv2.imread(args.generated, cv2.IMREAD_COLOR)
    h, w = original.shape[:2]
    warped, covered, inliers, matches, residual = align(original, generated, args.region)
    mask = np.zeros((h, w), np.float32)
    for x0, y0, x1, y1 in args.region:
        mask[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 1.0
    radius = max(3, int(args.feather * w))
    mask = cv2.GaussianBlur(mask * covered, (0, 0), radius / 2.0) * covered
    # Match the patch to the plate's colour where the two meet.
    ring = (mask > 0.05) & (mask < 0.6)
    if ring.any():
        for c in range(3):
            o = original[..., c][ring].astype(np.float32)
            g = warped[..., c][ring].astype(np.float32)
            gain = (o.std() + 1e-3) / (g.std() + 1e-3)
            offset = o.mean() - g.mean() * gain
            warped[..., c] = np.clip(warped[..., c].astype(np.float32) * gain + offset, 0, 255).astype(np.uint8)
    alpha = np.clip(mask * 255.0, 0, 255).astype(np.uint8)
    alpha[alpha < 3] = 0
    layer = np.dstack([warped, alpha])
    layer[alpha == 0] = 0
    cv2.imwrite(args.layer, layer)
    if args.preview:
        blended = original.astype(np.float32) * (1 - mask[..., None]) + warped.astype(np.float32) * mask[..., None]
        cv2.imwrite(args.preview, np.clip(blended, 0, 255).astype(np.uint8))
    print(f"matches {matches} inliers {inliers} median residual {residual:.2f}px -> {args.layer}")


if __name__ == "__main__":
    main()
