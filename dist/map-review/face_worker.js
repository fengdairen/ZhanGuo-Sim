/* face_worker.js —— 在 Worker 里跑平面划分，避免卡住界面 */
importScripts('arrangement.js');

self.onmessage = function (e) {
  const d = e.data || {};
  try {
    const res = self.Arrangement.build(d.lines || [], d.opts || {});
    const faces = res.faces.map(f => {
      const c = self.Arrangement.representative(f);
      return { ring: f.ring, area: f.area, center: c };
    });
    self.postMessage({ ok: true, faces: faces, stats: res.stats });
  } catch (err) {
    self.postMessage({ ok: false, error: String(err && err.message || err) });
  }
};
