/**
 * Nuancier RAL Classic, la référence que les magasins de peinture équipés d'une machine à
 * teinter savent reproduire. Valeurs écran (sRGB) approximatives, publiées par W3Schools
 * (https://www.w3schools.com/colors/colors_ral.asp) : la teinte exacte se vérifie toujours sur
 * un nuancier imprimé. Les teintes fluorescentes, nacrées et aluminium, faites pour la
 * signalisation ou le métal, sont laissées de côté : elles ne conviennent pas à un mur.
 */
export const RAL: readonly (readonly [code: string, nom: string, hex: string])[] = [
  ['1000', 'Beige vert', '#ccc58f'], ['1001', 'Beige', '#d1bc8a'], ['1002', 'Jaune sable', '#d2b773'],
  ['1003', 'Jaune de sécurité', '#f7ba0b'], ['1004', 'Jaune or', '#e2b007'], ['1005', 'Jaune miel', '#c89f04'],
  ['1006', 'Jaune maïs', '#e1a100'], ['1007', 'Jaune narcisse', '#e79c00'], ['1011', 'Beige brun', '#af8a54'],
  ['1012', 'Jaune citron', '#d9c022'], ['1013', 'Blanc perlé', '#e9e5ce'], ['1014', 'Ivoire', '#dfcea1'],
  ['1015', 'Ivoire clair', '#eadebd'], ['1016', 'Jaune soufre', '#eaf044'], ['1017', 'Jaune safran', '#f4b752'],
  ['1018', 'Jaune zinc', '#f3e03b'], ['1019', 'Beige gris', '#a4957d'], ['1020', 'Jaune olive', '#9a9464'],
  ['1021', 'Jaune colza', '#eec900'], ['1023', 'Jaune signalisation', '#f0ca00'], ['1024', 'Jaune ocre', '#b89c50'],
  ['1027', 'Jaune curry', '#a38c15'], ['1028', 'Jaune melon', '#ffab00'], ['1032', 'Jaune genêt', '#ddb20f'],
  ['1033', 'Jaune dahlia', '#faab21'], ['1034', 'Jaune pastel', '#edab56'], ['1037', 'Jaune soleil', '#eea205'],
  ['2000', 'Orangé jaune', '#dd7907'], ['2001', 'Orangé rouge', '#be4e20'], ['2002', 'Orangé sang', '#c63927'],
  ['2003', 'Orangé pastel', '#fa842b'], ['2004', 'Orangé pur', '#e75b12'], ['2008', 'Orangé rouge clair', '#f3752c'],
  ['2009', 'Orangé signalisation', '#e15501'], ['2010', 'Orangé de sécurité', '#d4652f'], ['2011', 'Orangé foncé', '#ec7c25'],
  ['2012', 'Orangé saumon', '#db6a50'], ['3000', 'Rouge feu', '#ab2524'], ['3001', 'Rouge de sécurité', '#a02128'],
  ['3002', 'Rouge carmin', '#a1232b'], ['3003', 'Rouge rubis', '#8d1d2c'], ['3004', 'Rouge pourpre', '#701f29'],
  ['3005', 'Rouge vin', '#5e2028'], ['3007', 'Rouge noir', '#402225'], ['3009', 'Rouge oxyde', '#703731'],
  ['3011', 'Rouge brun', '#7e292c'], ['3012', 'Rouge beige', '#cb8d73'], ['3013', 'Rouge tomate', '#9c322e'],
  ['3014', 'Vieux rose', '#d47479'], ['3015', 'Rose clair', '#e1a6ad'], ['3016', 'Rouge corail', '#ac4034'],
  ['3017', 'Rosé', '#d3545f'], ['3018', 'Rouge fraise', '#d14152'], ['3020', 'Rouge signalisation', '#c1121c'],
  ['3022', 'Rouge saumon', '#d56d56'], ['3027', 'Rouge framboise', '#b42041'], ['3028', 'Rouge pur', '#e72512'],
  ['3031', 'Rouge oriental', '#ac323b'], ['4001', 'Lilas rouge', '#8a5a83'], ['4002', 'Violet rouge', '#933d50'],
  ['4003', 'Violet bruyère', '#d15b8f'], ['4004', 'Violet bordeaux', '#691639'], ['4005', 'Lilas bleu', '#83639d'],
  ['4006', 'Pourpre signalisation', '#992572'], ['4007', 'Violet pourpre', '#4a203b'], ['4008', 'Violet de sécurité', '#904684'],
  ['4009', 'Violet pastel', '#a38995'], ['4010', 'Télémagenta', '#c63678'], ['5000', 'Bleu violet', '#384c70'],
  ['5001', 'Bleu vert', '#1f4764'], ['5002', 'Bleu outremer', '#2b2c7c'], ['5003', 'Bleu saphir', '#2a3756'],
  ['5004', 'Bleu noir', '#1d1f2a'], ['5005', 'Bleu de sécurité', '#154889'], ['5007', 'Bleu brillant', '#41678d'],
  ['5008', 'Bleu gris', '#313c48'], ['5009', 'Bleu azur', '#2e5978'], ['5010', 'Bleu gentiane', '#13447c'],
  ['5011', 'Bleu acier', '#232c3f'], ['5012', 'Bleu clair', '#3481b8'], ['5013', 'Bleu cobalt', '#232d53'],
  ['5014', 'Bleu pigeon', '#6c7c98'], ['5015', 'Bleu ciel', '#2874b2'], ['5017', 'Bleu signalisation', '#0e518d'],
  ['5018', 'Bleu turquoise', '#21888f'], ['5019', 'Bleu capri', '#1a5784'], ['5020', 'Bleu océan', '#0b4151'],
  ['5021', "Bleu d'eau", '#07737a'], ['5022', 'Bleu nocturne', '#2f2a5a'], ['5023', 'Bleu distant', '#4d668e'],
  ['5024', 'Bleu pastel', '#6a93b0'], ['6000', 'Vert patine', '#327662'], ['6001', 'Vert émeraude', '#28713e'],
  ['6002', 'Vert feuillage', '#276235'], ['6003', 'Vert olive', '#4b573e'], ['6004', 'Vert bleu', '#0e4243'],
  ['6005', 'Vert mousse', '#0f4336'], ['6006', 'Olive gris', '#40433b'], ['6007', 'Vert bouteille', '#283424'],
  ['6008', 'Vert brun', '#35382e'], ['6009', 'Vert sapin', '#26392f'], ['6010', 'Vert herbe', '#3e753b'],
  ['6011', 'Vert réséda', '#68825b'], ['6012', 'Vert noir', '#31403d'], ['6013', 'Vert jonc', '#797c5a'],
  ['6014', 'Olive jaune', '#444337'], ['6015', 'Olive noir', '#3d403a'], ['6016', 'Vert turquoise', '#026a52'],
  ['6017', 'Vert mai', '#468641'], ['6018', 'Vert jaune', '#48a43f'], ['6019', 'Vert blanc', '#b7d9b1'],
  ['6020', 'Vert oxyde chromique', '#354733'], ['6021', 'Vert pâle', '#86a47c'], ['6022', 'Olive brun', '#3e3c32'],
  ['6024', 'Vert signalisation', '#008754'], ['6025', 'Vert fougère', '#53753c'], ['6026', 'Vert opale', '#005d52'],
  ['6027', 'Vert clair', '#81c0bb'], ['6028', 'Vert pin', '#2d5546'], ['6029', 'Vert menthe', '#007243'],
  ['6032', 'Vert de sécurité', '#0f8558'], ['6033', 'Turquoise menthe', '#478a84'], ['6034', 'Turquoise pastel', '#7fb0b2'],
  ['7000', 'Gris petit-gris', '#7e8b92'], ['7001', 'Gris argent', '#8f999f'], ['7002', 'Gris olive', '#817f68'],
  ['7003', 'Gris mousse', '#7a7b6d'], ['7004', 'Gris de sécurité', '#9ea0a1'], ['7005', 'Gris souris', '#6b716f'],
  ['7006', 'Gris beige', '#756f61'], ['7008', 'Gris kaki', '#746643'], ['7009', 'Gris vert', '#5b6259'],
  ['7010', 'Gris tente', '#575d57'], ['7011', 'Gris fer', '#555d61'], ['7012', 'Gris basalte', '#596163'],
  ['7013', 'Gris brun', '#555548'], ['7015', 'Gris ardoise', '#51565c'], ['7016', 'Gris anthracite', '#373f43'],
  ['7021', 'Gris noir', '#2e3234'], ['7022', "Gris terre d'ombre", '#4b4d46'], ['7023', 'Gris béton', '#818479'],
  ['7024', 'Gris graphite', '#474a50'], ['7026', 'Gris granit', '#374447'], ['7030', 'Gris pierre', '#939388'],
  ['7031', 'Gris bleu', '#5d6970'], ['7032', 'Gris silex', '#b9b9a8'], ['7033', 'Gris ciment', '#818979'],
  ['7034', 'Gris jaune', '#939176'], ['7035', 'Gris clair', '#cbd0cc'], ['7036', 'Gris platine', '#9a9697'],
  ['7037', 'Gris poussière', '#7c7f7e'], ['7038', 'Gris agate', '#b4b8b0'], ['7039', 'Gris quartz', '#6b695f'],
  ['7040', 'Gris fenêtre', '#9da3a6'], ['7042', 'Gris signalisation A', '#8f9695'], ['7043', 'Gris signalisation B', '#4e5451'],
  ['7044', 'Gris soie', '#bdbdb2'], ['7045', 'Télégris 1', '#91969a'], ['7046', 'Télégris 2', '#82898e'],
  ['7047', 'Télégris 4', '#cfd0cf'], ['8000', 'Brun vert', '#887142'], ['8001', 'Brun terre de Sienne', '#9c6b30'],
  ['8002', 'Brun de sécurité', '#7b5141'], ['8003', 'Brun argile', '#80542f'], ['8004', 'Brun cuivré', '#8f4e35'],
  ['8007', 'Brun fauve', '#6f4a2f'], ['8008', 'Brun olive', '#6f4f28'], ['8011', 'Brun noisette', '#5a3a29'],
  ['8012', 'Brun rouge', '#673831'], ['8014', 'Brun sépia', '#49392d'], ['8015', 'Marron', '#633a34'],
  ['8016', 'Brun acajou', '#4c2f26'], ['8017', 'Brun chocolat', '#44322d'], ['8019', 'Brun gris', '#3f3a3a'],
  ['8022', 'Brun noir', '#211f20'], ['8023', 'Brun orangé', '#a65e2f'], ['8024', 'Brun beige', '#79553c'],
  ['8025', 'Brun pâle', '#755c49'], ['8028', 'Brun terre', '#4e3b31'], ['9001', 'Blanc crème', '#fdf4e3'],
  ['9002', 'Blanc gris', '#e7ebda'], ['9003', 'Blanc de sécurité', '#f4f4f4'], ['9004', 'Noir de sécurité', '#282828'],
  ['9005', 'Noir foncé', '#0a0a0a'], ['9010', 'Blanc pur', '#ffffff'], ['9011', 'Noir graphite', '#1c1c1c'],
  ['9016', 'Blanc signalisation', '#f6f6f6'], ['9017', 'Noir signalisation', '#1e1e1e'], ['9018', 'Blanc papyrus', '#d7d7d7'],
]

export interface TeinteRal {
  code: string // « RAL 5015 »
  nom: string
  hex: string
  ecart: number // 0 : identique ; au-delà de 15, la différence se voit nettement
}

/** La référence RAL la plus proche d'une couleur, à l'œil (écart OKLab). */
export function ralLePlusProche(hexa: string): TeinteRal {
  let meilleure: TeinteRal | null = null
  for (const [code, nom, hex] of RAL) {
    const e = ecart(hexa, hex)
    if (!meilleure || e < meilleure.ecart) meilleure = { code: `RAL ${code}`, nom, hex, ecart: e }
  }
  return meilleure!
}

/** Ce que l'écart veut dire pour l'œil, en mots. */
export function proximite(ecartPercu: number): string {
  if (ecartPercu <= 3) return 'identique à l\'œil'
  if (ecartPercu <= 8) return 'très proche'
  if (ecartPercu <= 15) return 'proche'
  return 'la plus proche, un peu différente'
}
