# verbatim — convertir et vérifier un lot

Pour les auxiliaires de recherche. Aucune programmation requise.

## Une seule fois, sur votre poste

Le README décrit l'installation pas à pas, clic par clic. En bref :

1. Installez Python depuis https://www.python.org/downloads/ — sous Windows,
   cochez **Add python.exe to PATH** sur le premier écran.
2. Dans le Terminal (Mac) ou l'Invite de commandes (Windows), collez cette
   ligne entière et appuyez sur Entrée :
   - Mac : `python3 -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"`
   - Windows : `py -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"`

   Ne lancez **pas** `pip install verbatim` seul : ce nom appartient à un autre
   logiciel, sans rapport, et vous installeriez le mauvais outil.
3. Tesseract ne sert qu'à *vérifier* les PDF numérisés, pas à les convertir —
   voir le README. Convertir une numérisation nécessite une clé Mistral.

Si `verbatim` est ensuite « introuvable », utilisez `python3 -m verbatim` (Mac)
ou `py -m verbatim` (Windows) à la place.

## À chaque utilisation

Tapez `verbatim` et appuyez sur Entrée. Une fenêtre s'ouvre. Le menu en haut à
droite permet de passer en français ; votre choix est retenu.

### Convertir

1. Choisissez le dossier contenant les PDF, puis le dossier de sortie des TXT.
2. Choisissez le format de sortie : **Décisions des COP** ou **Textes d'accords**.
3. Cliquez sur **Convertir**.

Le journal indique ce qui est arrivé à chaque fichier. À la fin, il annonce
combien ont été convertis et combien sont à vérifier.

### Vérifier

L'onglet **Vérifier** s'ouvre sur les fichiers à examiner, les plus douteux en
premier. Il fonctionne avec n'importe quel dossier de fichiers `.txt`, y compris
ceux produits par d'autres outils : choisissez alors le dossier contenant les PDF
correspondants dans **Dossier des PDF** (mêmes noms de fichiers), ou cochez
**Vérifier le texte seulement (sans PDF)**.

- ✗ signale un problème. **!** signale quelque chose à regarder.
  ✓ signifie : comparé au PDF, rien à signaler. ○ signifie que le texte semble
  correct mais n'a pas encore été comparé à son PDF. ☑ signifie que vous l'avez
  déjà vérifié.
- La liste du haut indique quoi examiner, et à quelle page.
- Cliquez sur une ligne. La page s'affiche à gauche, le passage entouré, et le
  même passage est surligné dans le texte à droite. **Comparez seulement ce
  paragraphe** : inutile de lire tout le fichier.
- Un fond **mauve** signale des mots produits par un modèle plutôt que lus dans
  le PDF. Rien dans le document ne peut les confirmer : vérifiez-les tous.
- **Afficher** ne garde qu'un type de problème à la fois : une série de fichiers
  au même défaut se juge bien plus vite qu'une liste mélangée.
- **Fiabilité minimale de la numérisation** fixe le seuil à partir duquel la
  lecture d'une numérisation sert à vérifier le texte. En dessous, verbatim dit
  que la numérisation n'a pas pu être lue plutôt que de signaler de fausses
  erreurs.
- Dans l'aperçu du PDF, déplacez-vous avec deux doigts sur le pavé tactile, ou
  en faisant glisser la page.
- Inscrivez votre nom dans **Vérifié par** (il est retenu) et, si utile, une
  **Remarque**. Cliquez ensuite sur **Accepter**, **À retravailler** ou
  **Rejeter**. Le fichier suivant s'ouvre automatiquement.

**Résumé…** indique ce qu'il est advenu du dossier — combien de fichiers ont été
vérifiés, par qui, comment ils ont été décidés, et où vous n'êtes pas d'accord
avec l'outil — et exporte une ligne par fichier en CSV, pour un tableur.

Pour les fichiers convertis par verbatim, votre décision est enregistrée à côté
du fichier. Pour les autres, les vérifications et votre décision sont
enregistrées **sur votre ordinateur seulement** : rien n'est écrit dans le
dossier, et vos collègues ne voient pas ces décisions.

## Ce que signalent les messages

| Message | Signification |
| --- | --- |
| *N mot(s) du texte ne figurent pas dans le PDF* | Des mots sont apparus alors qu'ils ne sont pas dans la source. Le constat le plus grave : vérifiez-les sur la page. |
| *N mot(s) du PDF ne figurent pas dans le texte* | Quelque chose a été perdu. Parfois légitime (un en-tête retiré) ; vérifiez la page. |
| *N nombre(s) du texte ne figurent pas dans le PDF* | Un nombre ou une date absent de la source. À vérifier systématiquement. |
| *N page(s) ont été produites par un modèle* | Ces pages n'ont pas été lues dans le PDF mais générées. Vérifiez chaque mot. |
| *N mot(s) semblent brouillés* | Le texte du PDF lui-même est abîmé et entremêle deux lignes. Reconvertissez avec **Reconnaître le texte** réglé sur *always*. |
| *les mêmes N mots se répètent sans fin* | La reconnaissance a bouclé. Reconvertissez le fichier. |
| *un tableau a N % de ses cellules remplies avec la même valeur* | Une reconnaissance incapable de lire le tableau a pu en inventer le contenu. Comparez avec la page. |
| *N mot(s) ici seraient inattendus dans ce type de document* | Des mots qui n'apparaissent nulle part dans les textes de référence. Souvent le signe d'un texte inventé : lisez ce passage. |
| *la reconnaissance n'est sûre qu'à N %* | Numérisation de mauvaise qualité. Lisez attentivement. |

## Si le résultat semble incorrect

| Problème | Essayez |
| --- | --- |
| Deux colonnes sont mélangées | Réglez **Colonnes** sur 2 |
| Le texte est découpé alors qu'il ne devrait pas | Réglez **Colonnes** sur 1 |
| Un tableau est rendu comme du texte courant | Réglez **Tableaux** sur *text* — seulement si la page est presque entièrement un tableau |
| Un titre a disparu | Cochez **conserver en-têtes et pieds de page** |
| Le texte est illisible dès le début | Réglez **Reconnaître le texte** sur *always* |
| Vous avez besoin des numéros de page pour citer | Cochez **marqueurs [page N]** |

Si une numérisation est vraiment mauvaise, demandez à David avant d'utiliser
l'option Mistral : elle est facturée à la page, et il s'agit d'un modèle et non
d'un lecteur de caractères, donc tout ce qu'elle produit doit être vérifié à la
main.
