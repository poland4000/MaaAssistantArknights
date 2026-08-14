// Focus Guard: when Arknights activates programmatically (MAA synthetic input),
// hand focus straight back to the previously active window.
// A real user click is identified by the cursor being over the game window.
var prevWindow = null;
workspace.windowActivated.connect(function(w) {
    var isGame = String(w.resourceClass) === "steam_proton" && String(w.caption).indexOf("Arknights") === 0;
    if (!isGame) {
        prevWindow = w;
        return;
    }
    if (!prevWindow) {
        return;
    }
    var deleted = false;
    try { deleted = prevWindow.deleted; } catch (e) { deleted = true; }
    if (deleted) {
        prevWindow = null;
        return;
    }
    var c = workspace.cursorPos;
    var g = w.frameGeometry;
    var cursorOverGame = c.x >= g.x && c.x <= g.x + g.width && c.y >= g.y && c.y <= g.y + g.height;
    if (!cursorOverGame) {
        workspace.activeWindow = prevWindow;
    }
});
