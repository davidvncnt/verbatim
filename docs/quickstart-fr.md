# verbatim — convertir et vérifier un lot

Pour les auxiliaires de recherche. Aucune programmation requise.

## Une seule fois, sur votre poste

1. Installez Python 3.10 ou plus récent depuis python.org.
2. Ouvrez le Terminal (macOS) ou l'Invite de commandes (Windows) et lancez :

   ```
   pip install verbatim
   ```

3. Seulement si vous convertirez des PDF **numérisés**, installez aussi
   Tesseract :
   - macOS : `brew install tesseract tesseract-lang`
   - Windows : téléchargez l'installateur sur
     https://github.com/UB-Mannheim/tesseract/wiki, puis lancez
     `pip install pytesseract`

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
premier.

- ✗ signale un problème. **!** signale quelque chose à regarder.
  ✓ signifie que rien n'a été relevé. ☑ signifie que vous l'avez déjà vérifié.
- La liste du haut indique quoi examiner, et à quelle page.
- Cliquez sur une ligne. La page s'affiche à gauche, le passage entouré, et le
  même passage est surligné dans le texte à droite. **Comparez seulement ce
  paragraphe** : inutile de lire tout le fichier.
- Un fond **mauve** signale des mots produits par un modèle plutôt que lus dans
  le PDF. Rien dans le document ne peut les confirmer : vérifiez-les tous.
- Inscrivez votre nom une fois, puis cliquez sur **Accepter**, **À retravailler**
  ou **Rejeter**. Le fichier suivant s'ouvre automatiquement.

Votre décision est enregistrée à côté du fichier. Elle constitue la trace de qui
a vérifié quoi, et elle sert aussi à apprendre à l'outil quels fichiers sont
réellement mauvais.

## Ce que signalent les messages

| Message | Signification |
| --- | --- |
| *N mot(s) du texte ne figurent pas dans le PDF* | Des mots sont apparus alors qu'ils ne sont pas dans la source. Le constat le plus grave : vérifiez-les sur la page. |
| *N mot(s) du PDF ne figurent pas dans le texte* | Quelque chose a été perdu. Parfois légitime (un en-tête retiré) ; vérifiez la page. |
| *N nombre(s) du texte ne figurent pas dans le PDF* | Un nombre ou une date absent de la source. À vérifier systématiquement. |
| *N page(s) ont été produites par un modèle* | Ces pages n'ont pas été lues dans le PDF mais générées. Vérifiez chaque mot. |
| *N mot(s) semblent brouillés* | Le texte du PDF lui-même est abîmé et entremêle deux lignes. Reconvertissez avec **Reconnaître le texte** réglé sur *always*. |
| *les mêmes N mots se répètent sans fin* | La reconnaissance a bouclé. Reconvertissez le fichier. |
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
