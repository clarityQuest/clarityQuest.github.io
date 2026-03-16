// Initialize OpenSeadragon for DZI viewing
window.addEventListener('DOMContentLoaded', () => {
  OpenSeadragon({
    id: "openseadragon1",
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
    tileSources: "Tabula_Peutingeriana_-_Miller.dzi",
    showNavigator: true,
    defaultZoomLevel: 0,
    minZoomLevel: 0,
    maxZoomLevel: 40,
    visibilityRatio: 1.0,
    constrainDuringPan: true,
    blendTime: 0.1,
    animationTime: 0.5,
    backgroundColor: "#181818"
  });
});
