"""Write synthetic Y4M camera feeds for Chromium's fake capture device. usage: make_video.py OUTDIR"""
import sys, os, numpy as np
W, H, F = 320, 240, 15
def yuv(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.257*r + 0.504*g + 0.098*b + 16
    u = -0.148*r - 0.291*g + 0.439*b + 128
    v = 0.439*r - 0.368*g - 0.071*b + 128
    c = lambda a: a.clip(0, 255).astype(np.uint8)
    return c(y), c(u[::2, ::2]), c(v[::2, ::2])
def write(path, script, rgb=(217, 33, 33), extra=()):
    yy, xx = np.mgrid[0:H, 0:W]
    with open(path, 'wb') as f:
        f.write(b'YUV4MPEG2 W%d H%d F%d:1 Ip A1:1 C420jpeg\n' % (W, H, F))
        for secs, x in script:
            img = np.empty((H, W, 3), np.float32); img[:] = (120, 120, 125)
            img[(xx - x*W)**2 + (yy - H/2)**2 <= 24**2] = rgb
            for ex, ey, er, ergb in extra: img[(xx - ex)**2 + (yy - ey)**2 <= er**2] = ergb
            y, u, v = yuv(img); blob = b'FRAME\n' + y.tobytes() + u.tobytes() + v.tobytes()
            for _ in range(int(secs*F)): f.write(blob)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
walk = [(3, .5), (2, .5), (2, .17), (2, .83)]          # centre, centre, left, right  (loops)
write(f'{out}/walk.y4m', walk)
write(f'{out}/still.y4m', [(3, .5)])
write(f'{out}/stray.y4m', walk, extra=[(310, 30, 3, (217, 33, 33))])   # ~1 px at 160x120, far from the object
write(f'{out}/blue.y4m', walk, rgb=(30, 70, 220))
