# dist/site —— 可分享的只读舆图

把**整个目录**上传到任意静态托管即可，无需服务器、无需后端。

## 上传方式

**Cloudflare Pages（推荐，免费、支持私有仓库）**
1. 登录 dash.cloudflare.com → Workers & Pages → Create → Pages → Upload assets
2. 把 `dist/site` 里的文件全部拖进去
3. 得到 `https://<项目名>.pages.dev`，直接发给别人

**GitHub Pages**
1. 把本目录内容推到仓库的 `gh-pages` 分支（或 `main` 的 `/docs`）
2. 仓库 Settings → Pages → 选择对应分支
3. 得到 `https://<用户名>.github.io/<仓库名>/`

**任何静态托管**（Netlify / Vercel / 对象存储 + CDN）同理：只需要能托管静态文件。

## 目录内容

| 文件 | 说明 |
|---|---|
| `index.html` | 入口页 |
| `map.html` | 舆图本体（数据已内嵌，457 KB） |
| `mount.webp` | 山地纹理（4.3 MB） |
| `preview-*.png` | 预览缩略图 |

## 注意

- 全部是静态文件，**没有后端**，别人只能看不能改
- 想换域名：在托管平台上绑定即可，Cloudflare / GitHub 都免费给 HTTPS
- 使用中国大陆服务器时才需要 ICP 备案；海外托管不需要
- 重新生成：根目录运行 `发布舆图.cmd`
