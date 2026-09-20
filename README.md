# verbatim

verbatim convertit les PDF de textes d'accords environnementaux internationaux
et de décisions des COP en texte brut propre et fidèle, puis aide à vérifier le
résultat.

## À quoi sert verbatim

**Convertir des PDF en texte.** Vous choisissez un dossier de PDF, verbatim
produit un fichier `.txt` par document :

- un paragraphe par ligne, une ligne vide entre les paragraphes ;
- sans numéros de page, en-têtes ni pieds de page ;
- les tableaux conservés, alignés en colonnes ;
- les mots coupés en fin de ligne recollés, les paragraphes coupés par un
  changement de page réunis ;
- les mises en page à deux colonnes lues dans le bon ordre, les pages imprimées
  à l'horizontale redressées.

**Sans rien inventer.** Chaque mot du texte vient du PDF. Quand le PDF contient
du texte sélectionnable, verbatim le lit directement, sans intelligence
artificielle. Quand c'est une numérisation, les pages sont lues par Mistral, un
service payant qui demande une clé : c'est un modèle, et non un lecteur de
caractères, donc tout ce qu'il produit est signalé comme tel et doit être
vérifié.

**Repérer les inventions probables.** Quand le texte ne peut pas être comparé
mot à mot au PDF — sortie d'un modèle, numérisation illisible, PDF absent —
verbatim signale deux indices d'invention : un tableau dont presque toutes les
cellules contiennent la même valeur, et des mots qu'on ne s'attendrait pas à
lire dans ce type de document. Ce sont des raisons de regarder, jamais des
verdicts.

**Vérifier automatiquement chaque conversion.** verbatim contrôle chaque
fichier dès sa conversion et signale :

- des mots ou des nombres présents dans le texte mais absents du PDF ;
- des mots du PDF qui manquent dans le texte ;
- du texte brouillé ou répété en boucle ;
- des pages produites par un modèle plutôt que lues dans le PDF.

**Vérifier rapidement à l'écran.** L'onglet *Vérifier* présente les fichiers
les plus douteux en premier. Pour chaque problème, il affiche la page du PDF à
gauche, avec le passage entouré, et le texte à droite, avec le même passage
surligné : on compare un paragraphe, pas un document entier.

**Vérifier des fichiers texte existants.** L'onglet *Vérifier* fonctionne aussi
avec des fichiers `.txt` produits par d'autres outils. verbatim relit alors le
PDF correspondant et compare le texte avec lui. Si le PDF est une numérisation,
Tesseract — un lecteur de caractères gratuit et local — en fait une lecture
indépendante, qui sert à repérer les passages du texte qui n'existent nulle part
dans la numérisation. Quand la numérisation est trop abîmée pour être lue de
façon fiable, verbatim le dit au lieu de signaler de fausses erreurs.

L'interface est en français et en anglais.

---

## Installation

Il y a trois étapes. Les deux premières sont nécessaires ; la troisième ne sert
que si vous convertissez des **PDF numérisés** (des images de pages, sans texte
sélectionnable).

Suivez la partie qui correspond à votre ordinateur : **Mac** ou **Windows**.

### Sur Mac

#### Étape 1 — Installer Python

1. Allez sur https://www.python.org/downloads/
2. Cliquez sur le bouton jaune **Download Python 3.x.x**.
3. Ouvrez le fichier téléchargé (il se termine par `.pkg`) et suivez
   l'installation en cliquant sur **Continuer**, puis **Installer**.
4. À la fin, une fenêtre du Finder s'ouvre. Vous pouvez la fermer.

#### Étape 2 — Installer verbatim

1. Ouvrez l'application **Terminal** : appuyez sur `Cmd` + `Espace`, tapez
   `Terminal`, puis appuyez sur `Entrée`.
2. Copiez la ligne ci-dessous en entier, collez-la dans le Terminal
   (`Cmd` + `V`), puis appuyez sur `Entrée` :

   ```
   python3 -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"
   ```

3. Attendez que le Terminal ait fini d'écrire : la dernière ligne commence par
   `Successfully installed`.

> **Attention :** ne tapez pas `pip install verbatim` tout seul. Ce nom
> appartient à un autre logiciel, sans rapport, et vous installeriez le mauvais
> outil. Utilisez toujours la ligne complète ci-dessus.

#### Étape 3 (facultative) — Installer Tesseract, pour vérifier les numérisations

Tesseract ne sert pas à convertir : il sert à relire une numérisation de façon
indépendante, pour que l'onglet *Vérifier* puisse repérer un passage inventé.
Installez-le si vous vérifiez des documents numérisés. Il s'installe avec
Homebrew, un outil d'installation pour Mac.

1. Allez sur https://brew.sh
2. Copiez la commande affichée sous **Install Homebrew**, collez-la dans le
   Terminal et appuyez sur `Entrée`.
3. Le Terminal demande votre mot de passe du Mac. Tapez-le puis appuyez sur
   `Entrée` : **rien ne s'affiche pendant que vous tapez**, c'est normal.
4. Attendez la fin (plusieurs minutes). Si le Terminal affiche une section
   **Next steps** avec des commandes à exécuter, copiez-collez chacune d'elles
   et appuyez sur `Entrée` après chacune.
5. Copiez cette ligne dans le Terminal et appuyez sur `Entrée` :

   ```
   brew install tesseract tesseract-lang
   ```

### Sur Windows

#### Étape 1 — Installer Python

1. Allez sur https://www.python.org/downloads/
2. Cliquez sur le bouton jaune **Download Python 3.x.x**.
3. Ouvrez le fichier téléchargé (il se termine par `.exe`).
4. **Important :** en bas de la première fenêtre, cochez la case
   **Add python.exe to PATH**.
5. Cliquez sur **Install Now** et attendez la fin, puis sur **Close**.

#### Étape 2 — Installer verbatim

1. Ouvrez l'**Invite de commandes** : cliquez sur le menu Démarrer, tapez
   `cmd`, puis appuyez sur `Entrée`.
2. Copiez la ligne ci-dessous en entier, collez-la dans l'Invite de commandes
   (clic droit, ou `Ctrl` + `V`), puis appuyez sur `Entrée` :

   ```
   py -m pip install "verbatim[all] @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"
   ```

3. Attendez que l'installation se termine : la dernière ligne commence par
   `Successfully installed`.

> **Attention :** ne tapez pas `pip install verbatim` tout seul. Ce nom
> appartient à un autre logiciel, sans rapport, et vous installeriez le mauvais
> outil. Utilisez toujours la ligne complète ci-dessus.

#### Étape 3 (facultative) — Installer Tesseract, pour vérifier les numérisations

Tesseract ne sert pas à convertir : il sert à relire une numérisation de façon
indépendante, pour que l'onglet *Vérifier* puisse repérer un passage inventé.

1. Allez sur https://github.com/UB-Mannheim/tesseract/wiki
2. Téléchargez le programme d'installation pour Windows (le fichier se termine
   par `-w64-setup.exe`).
3. Ouvrez-le et cliquez sur **Next** jusqu'à l'écran **Choose Components**.
4. Dans cet écran, ouvrez **Additional language data** et cochez **French** et
   **Spanish**.
5. Continuez avec **Next** puis **Install**. **Ne changez pas le dossier
   d'installation proposé** : verbatim le trouve automatiquement.

### Vérifier que tout fonctionne

Dans le Terminal (Mac) ou l'Invite de commandes (Windows), tapez :

```
verbatim --version
```

La réponse doit être `verbatim` suivi d'un numéro de version.

Si vous obtenez plutôt *command not found* ou *n'est pas reconnu*, utilisez à
la place, ici et partout ailleurs :

- sur Mac : `python3 -m verbatim`
- sur Windows : `py -m verbatim`

### Mettre à jour verbatim

Relancez l'installation en forçant le remplacement de l'ancienne version :

- sur Mac :

  ```
  python3 -m pip install --force-reinstall --no-deps "verbatim @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"
  ```

- sur Windows :

  ```
  py -m pip install --force-reinstall --no-deps "verbatim @ https://github.com/davidvncnt/verbatim/archive/refs/heads/main.zip"
  ```

---

## Utilisation

Tapez `verbatim` dans le Terminal ou l'Invite de commandes et appuyez sur
`Entrée`. Une fenêtre s'ouvre. Le menu en haut à droite permet de choisir la
langue ; votre choix est retenu.

### Convertir

1. Dans **PDF dans**, choisissez le dossier qui contient les PDF.
2. Dans **TXT vers**, choisissez où enregistrer les fichiers texte. Laissez vide
   pour les enregistrer à côté des PDF.
3. Dans **Format de sortie**, choisissez **Décisions des COP** ou
   **Textes d'accords**.
4. Cliquez sur **Convertir**.

Les PDF numérisés (sans texte sélectionnable) nécessitent une **clé Mistral**,
à coller dans le champ prévu. Sans clé, ces pages restent vides et sont
signalées.

Le journal indique ce qui est arrivé à chaque fichier. À la fin, verbatim
annonce combien de fichiers ont été convertis et combien sont à vérifier, puis
ouvre l'onglet *Vérifier* sur ce dossier.

Chaque conversion produit deux fichiers : le texte (`nom.txt`) et, à côté, une
fiche (`nom.verbatim.json`) qui garde la trace des contrôles effectués et de
l'emplacement de chaque passage dans le PDF. **Gardez les deux ensemble**, et
gardez les PDF à côté : l'onglet *Vérifier* en a besoin.

### Vérifier

1. Dans l'onglet **Vérifier**, cliquez sur **Ouvrir un dossier de fichiers
   texte** et choisissez le dossier qui contient les fichiers `.txt`.
2. Si ces fichiers n'ont pas été convertis par verbatim, choisissez aussi, dans
   **Dossier des PDF**, le dossier qui contient les PDF correspondants. Chaque
   fichier texte est associé au PDF qui porte le même nom
   (`20001_rulesofprocedure_2006.txt` avec `20001_rulesofprocedure_2006.pdf`).
3. La liste de gauche présente les fichiers, les plus douteux en premier :

   | Marque | Signification |
   | --- | --- |
   | ✗ | problème détecté |
   | **!** | à regarder |
   | ✓ | comparé au PDF, rien à signaler |
   | ○ | le texte ne présente pas de défaut visible, mais n'a pas encore été comparé à son PDF |
   | ? | pas encore lu |
   | ☑ | déjà vérifié par vous |

   La première fois qu'un grand dossier est ouvert, verbatim le lit en arrière-plan
   pour le trier (quelques minutes pour 20 000 fichiers). Il s'en souvient
   ensuite.
4. **Afficher** ne garde qu'un type de problème à la fois (mots absents du PDF,
   mots brouillés, caractères mal décodés…) : une série de fichiers qui ont le
   même défaut se juge bien plus vite qu'une série de fichiers sans rapport.
5. Cliquez sur un fichier. S'il n'a pas été converti par verbatim, il est vérifié
   à ce moment-là : quelques secondes pour un PDF ordinaire, plus longtemps pour
   une numérisation, qui doit d'abord être lue par Tesseract. Une barre de
   progression indique l'avancement, et le résultat est conservé.
6. Cliquez sur un problème dans **À examiner**. La page s'affiche à gauche avec
   le passage entouré ; le même passage est surligné dans le texte à droite.
   Un fond **mauve** signale des mots produits par un modèle : vérifiez-les
   tous.
7. Inscrivez votre nom dans **Vérifié par** (il est retenu pour la prochaine
   fois) et, si utile, une **Remarque**.
8. Cliquez sur **Accepter**, **À retravailler** ou **Rejeter**. Le fichier
   suivant s'ouvre. La liste garde la trace de votre décision : ☑ accepté,
   ⊙ à retravailler, ☒ rejeté.

Dans l'aperçu du PDF, déplacez-vous avec deux doigts sur le pavé tactile, ou en
faisant glisser la page directement. Deux doigts vers le côté, en maintenant
**Maj**, déplacent la page horizontalement.

**Sans les PDF.** Cochez **Vérifier le texte seulement (sans PDF)** pour ne
faire que les contrôles qui n'ont pas besoin du PDF : texte répété en boucle,
mots brouillés, caractères mal décodés. Ils sont rapides, mais ils ne peuvent
pas repérer un passage bien écrit qui ne figure pas dans la source.

**Voir ce qui a été décidé.** Le bouton **Résumé…** indique, pour le dossier
ouvert, combien de fichiers ont été vérifiés et par qui, comment ils ont été
décidés, ce que verbatim avait trouvé, et sur combien de fichiers la personne et
l'outil ne sont pas d'accord. **Exporter en CSV…** écrit une ligne par fichier
(nom, verdict de l'outil, problèmes, décision, personne, remarque, date), à
ouvrir dans un tableur. En ligne de commande : `verbatim summary dossier_txt`,
avec `--csv fichier.csv` pour le tableau.

**Régler la confiance accordée aux numérisations.** Le champ **Fiabilité
minimale de la numérisation** (70 % par défaut) fixe le seuil à partir duquel
la lecture d'une numérisation par Tesseract est considérée comme une preuve.
Au-dessous, verbatim dit que la numérisation n'a pas pu être lue plutôt que de
signaler de fausses erreurs. Baissez-le si des vérifications utiles sont
écartées, montez-le si de fausses alertes apparaissent sur des numérisations
médiocres.

**Où sont enregistrées les décisions.**

- Pour les fichiers convertis par verbatim, la décision est enregistrée dans la
  fiche `nom.verbatim.json`, à côté du texte.
- Pour les autres fichiers, les vérifications et les décisions sont
  enregistrées **sur votre ordinateur seulement** : rien n'est écrit dans le
  dossier vérifié. Vos collègues ne voient donc pas les décisions que vous avez
  prises sur ces fichiers.

### En ligne de commande

Pour les grands lots, les mêmes fonctions existent sans fenêtre :

```
verbatim convert dossier_pdf -o dossier_txt
verbatim check dossier_txt
verbatim review dossier_txt
verbatim summary dossier_txt --csv resume.csv
verbatim vocabulary dossier_textes_acceptés
verbatim audit dossier_txt
```

`verbatim audit` mesure l'ensemble d'un corpus déjà converti et produit un
classement des fichiers les plus susceptibles d'être abîmés.

### Apprendre le vocabulaire attendu (facultatif)

Pour repérer les mots inattendus, verbatim doit savoir quels mots appartiennent
à ce type de document. Il l'apprend d'un dossier de textes que vous jugez
corrects :

```
verbatim vocabulary /chemin/vers/les/textes/acceptés
```

Une seule fois, environ dix secondes pour 20 000 fichiers. Le vocabulaire reste
sur votre ordinateur. Sans lui, la vérification des mots inattendus ne
s'exécute simplement pas.

**Prenez des textes dans toutes les langues que vous convertissez.** Un
vocabulaire appris sur des documents anglais signalera des mots français
parfaitement normaux.

Mesuré sur le corpus existant : un document correct ne contient aucun mot
inattendu dans la moitié des cas, et 0,2 % des documents corrects en
contiennent assez pour être signalés. Les noms propres et les noms
scientifiques (*Dissostichus mawsoni*) sont ignorés.
