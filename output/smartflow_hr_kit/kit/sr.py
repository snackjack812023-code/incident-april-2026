"""4x super-resolution with Real-ESRGAN "realesr-general-x4v3" (SRVGGNetCompact, BSD-3 licence, xinntao/Real-ESRGAN),
run in pure NumPy: the .pth checkpoint is read without PyTorch and the 34-conv network is evaluated as shifted matmuls.
usage: python3 sr.py in.png out.png        (or import upscale4(img_rgb_uint8) -> uint8)"""
import io, os, pickle, sys, zipfile, collections
import numpy as np
from PIL import Image

MODEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'realesr-general-x4v3.pth')

def load_state_dict(path):
    """minimal reader for torch's zip checkpoint format (float32 tensors only)"""
    z = zipfile.ZipFile(path); root = z.namelist()[0].split('/')[0]
    storages = {}
    def storage(key, numel):
        if key not in storages:
            storages[key] = np.frombuffer(z.read(f'{root}/data/{key}'), dtype='<f4')
        return storages[key]
    def rebuild_tensor(st, offset, size, stride, *args):
        if len(size) == 0: return st[offset:offset + 1].reshape(())
        return np.lib.stride_tricks.as_strided(st[offset:], shape=tuple(size), strides=tuple(s * 4 for s in stride)).copy()
    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if name == '_rebuild_tensor_v2': return rebuild_tensor
            if name == '_rebuild_parameter': return lambda t, *a: t
            if mod == 'collections' and name == 'OrderedDict': return collections.OrderedDict
            if mod == 'torch' and name.endswith('Storage'): return name
            return super().find_class(mod, name)
        def persistent_load(self, pid):
            _, stype, key, loc, numel = pid
            if stype not in ('FloatStorage',): raise ValueError('unsupported storage ' + str(stype))
            return storage(key, numel)
    sd = U(io.BytesIO(z.read(f'{root}/data.pkl'))).load()
    return sd.get('params_ema') or sd.get('params') or sd

_W = None
def weights():
    global _W
    if _W is None:
        sd = load_state_dict(MODEL)
        idx = sorted({int(k.split('.')[1]) for k in sd if k.startswith('body.')})
        layers = []
        for i in idx:
            w = sd[f'body.{i}.weight']
            if w.ndim == 4:   # conv: (Cout, Cin, 3, 3) -> 9 x (Cin, Cout)
                layers.append(('conv', [np.ascontiguousarray(w[:, :, ky, kx].T) for ky in range(3) for kx in range(3)], sd[f'body.{i}.bias']))
            else:             # PReLU slope per channel
                layers.append(('prelu', w.astype(np.float32), None))
        _W = layers
    return _W

def conv3x3(x, ws, b):
    H, W, C = x.shape; xp = np.pad(x, ((1, 1), (1, 1), (0, 0)), mode='constant')
    out = np.empty((H * W, ws[0].shape[1]), np.float32); out[:] = b
    for k, w in enumerate(ws):
        ky, kx = divmod(k, 3)
        out += xp[ky:ky + H, kx:kx + W, :].reshape(-1, C) @ w
    return out.reshape(H, W, -1)

def upscale4(img):
    """img: HxWx3 uint8 RGB -> 4Hx4Wx3 uint8"""
    x = img.astype(np.float32) / 255.0; h = x
    for kind, w, b in weights():
        if kind == 'conv': h = conv3x3(h, w, b)
        else: h = np.where(h >= 0, h, h * w)
    H, W, _ = x.shape
    out = h.reshape(H, W, 3, 4, 4).transpose(0, 3, 1, 4, 2).reshape(H * 4, W * 4, 3)   # PixelShuffle(4), torch channel order
    out += np.repeat(np.repeat(x, 4, axis=0), 4, axis=1)                                # + nearest-upsampled input (residual)
    return np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)

def upscale4_tiled(img, tile=192, pad=12):
    """same result in tiles (bounded memory); tiles overlap by `pad` px of context on each side"""
    H, W, _ = img.shape; out = np.zeros((H * 4, W * 4, 3), np.uint8)
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(H, y0 + tile), min(W, x0 + tile)
            a0, b0, a1, b1 = max(0, y0 - pad), max(0, x0 - pad), min(H, y1 + pad), min(W, x1 + pad)
            t = upscale4(img[a0:a1, b0:b1])
            out[y0 * 4:y1 * 4, x0 * 4:x1 * 4] = t[(y0 - a0) * 4:(y0 - a0 + y1 - y0) * 4, (x0 - b0) * 4:(x0 - b0 + x1 - x0) * 4]
    return out

if __name__ == '__main__':
    import time
    t0 = time.time(); src = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
    out = upscale4_tiled(src) if src.shape[0] * src.shape[1] > 300_000 else upscale4(src)
    Image.fromarray(out).save(sys.argv[2]); print(f'sr x4: {src.shape[1]}x{src.shape[0]} -> {out.shape[1]}x{out.shape[0]} in {time.time() - t0:.1f}s')
