/**
 * Réduit une photo sur l'appareil avant de l'envoyer : une photo de téléphone pèse plusieurs
 * mégaoctets, bien trop pour un réseau lent. Le plus grand côté est ramené à 1600 pixels et
 * l'image réencodée en JPEG (quelques centaines de kilo-octets). Si l'appareil ne sait pas la
 * lire, le fichier d'origine part tel quel : le serveur vérifie et réencode de toute façon.
 */
export async function reduireImage(fichier: File, cote = 1600, qualite = 0.82): Promise<Blob> {
  try {
    const image = await createImageBitmap(fichier, { imageOrientation: 'from-image' })
    const echelle = Math.min(1, cote / Math.max(image.width, image.height))
    if (echelle === 1 && fichier.size < 600_000) return fichier
    const toile = document.createElement('canvas')
    toile.width = Math.round(image.width * echelle)
    toile.height = Math.round(image.height * echelle)
    const dessin = toile.getContext('2d')
    if (!dessin) return fichier
    // Fond blanc : un logo transparent ne devient pas noir en JPEG.
    dessin.fillStyle = '#ffffff'
    dessin.fillRect(0, 0, toile.width, toile.height)
    dessin.drawImage(image, 0, 0, toile.width, toile.height)
    image.close()
    const reduite = await new Promise<Blob | null>(resolve => toile.toBlob(resolve, 'image/jpeg', qualite))
    return reduite && reduite.size < fichier.size ? reduite : fichier
  } catch {
    return fichier
  }
}
