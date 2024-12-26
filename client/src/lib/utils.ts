export function getPlayerUUID(): string {
    let uuid = localStorage.getItem('playerUUID');
    if (!uuid) {
        uuid = crypto.randomUUID();
        localStorage.setItem('playerUUID', uuid);
    }
    return uuid;
}