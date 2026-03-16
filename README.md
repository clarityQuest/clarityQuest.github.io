# Tabula Peutingeriana

A minimal web app to view the Tabula Peutingeriana with scroll and zoom, using OpenSeadragon and a high-resolution open-licensed image.

## Features
- Pan and zoom the ancient Roman map
- Simple, responsive UI

## Usage
1. Start a simple local server from the `public` folder, for example:
	`python -m http.server 8000`
2. Open `http://localhost:8000` in your browser.
3. Pan and zoom the map using your mouse or touch.

## Deploy To GitHub Pages
This repository is configured with a GitHub Actions workflow that deploys the `public/` folder.

1. Create or rename your GitHub repository to exactly:
	`<your-username>.github.io`
2. Push this project to that repository (branch: `main`).
3. In GitHub, go to `Settings > Pages`.
4. Set `Source` to `GitHub Actions`.
5. After each push to `main`, deployment runs automatically.
6. Your site will be available at:
	`https://<your-username>.github.io/`

Notes:
- `public/.nojekyll` is included to ensure static assets are served as-is.
- Keep `index.html`, `.dzi`, and the `_files` tile folder inside `public/`.
- If your repo is not named `<your-username>.github.io`, GitHub will publish at a subpath (`/<repo>/`) instead of root.

## Credits
- Map image: Public domain, via Wikimedia Commons
- Viewer: [OpenSeadragon](https://openseadragon.github.io/)

---

Project name: **Tabula Peutingeriana**
