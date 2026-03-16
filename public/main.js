// Initialize OpenSeadragon for DZI viewing.
window.addEventListener('DOMContentLoaded', () => {
  const isFileProtocol = window.location.protocol === 'file:';
  const statusEl = document.getElementById('status');

  // Inline Deep Zoom metadata avoids fetching the .dzi file over XHR,
  // which commonly fails under file:// in browsers.
  const inlineTileSource = {
    Image: {
      xmlns: 'http://schemas.microsoft.com/deepzoom/2008',
      Url: 'Tabula_Peutingeriana_-_Miller_files/',
      Format: 'jpeg',
      Overlap: '1',
      TileSize: '254',
      Size: {
        Width: '46380',
        Height: '2953'
      }
    }
  };

  const viewer = OpenSeadragon({
    id: 'openseadragon1',
    prefixUrl: 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/',
    showNavigationControl: false,
    tileSources: isFileProtocol ? inlineTileSource : 'Tabula_Peutingeriana_-_Miller.dzi',
    showNavigator: true,
    defaultZoomLevel: 0,
    minZoomLevel: 0,
    maxZoomLevel: 40,
    visibilityRatio: 1.0,
    constrainDuringPan: true,
    blendTime: 0.1,
    animationTime: 0.5,
    backgroundColor: '#181818'
  });

  const btnZoomIn = document.getElementById('control-zoom-in');
  const btnZoomOut = document.getElementById('control-zoom-out');
  const btnHome = document.getElementById('control-home');
  const btnFullpage = document.getElementById('control-fullpage');

  if (btnZoomIn) {
    btnZoomIn.addEventListener('click', () => {
      viewer.viewport.zoomBy(1.2);
      viewer.viewport.applyConstraints();
    });
  }

  if (btnZoomOut) {
    btnZoomOut.addEventListener('click', () => {
      viewer.viewport.zoomBy(0.8);
      viewer.viewport.applyConstraints();
    });
  }

  if (btnHome) {
    btnHome.addEventListener('click', () => {
      viewer.viewport.goHome();
    });
  }

  if (btnFullpage) {
    btnFullpage.addEventListener('click', () => {
      const fullPage = viewer.isFullPage ? viewer.isFullPage() : false;
      if (viewer.setFullScreen) {
        viewer.setFullScreen(!fullPage);
      } else if (viewer.setFullPage) {
        viewer.setFullPage(!fullPage);
      }
    });

    viewer.addHandler('full-page', (event) => {
      btnFullpage.setAttribute('aria-pressed', event && event.fullPage ? 'true' : 'false');
    });
  }

  // If tiled loading still fails for any reason, fall back automatically
  // so users can always see the map without setup steps.
  let usedFallback = false;
  viewer.addHandler('open-failed', () => {
    if (usedFallback) {
      return;
    }
    usedFallback = true;
    viewer.open({
      type: 'image',
      url: 'Tabula_Peutingeriana_-_Miller.jpg'
    });
    if (statusEl) {
      statusEl.textContent = 'Loaded fallback image mode.';
      statusEl.classList.add('visible');
    }
  });
});
