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
artificielle. Quand c'est une numérisation, le texte est reconnu à partir de
l'image par Tesseract, un logiciel de reconnaissance de caractères. Un modèle
d'IA (Mistral) peut être utilisé en option pour les numérisations de mauvaise
qualité ; tout ce qu'il produit est alors signalé et doit être vérifié.

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
PDF correspondant et compare le texte avec lui ; si le PDF est une
numérisation, il en reconnaît d'abord le texte avec Tesseract.

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

#### Étape 3 (facultative) — Installer Tesseract, pour les PDF numérisés

Tesseract s'installe avec Homebrew, un outil d'installation pour Mac.

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

#### Étape 3 (facultative) — Installer Tesseract, pour les PDF numérisés

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
4. Cliquez sur un fichier. S'il n'a pas été converti par verbatim, il est vérifié
   à ce moment-là : quelques secondes pour un PDF ordinaire, plus longtemps pour
   une numérisation, qui doit d'abord être lue par Tesseract. Une barre de
   progression indique l'avancement, et le résultat est conservé.
5. Cliquez sur un problème dans **À examiner**. La page s'affiche à gauche avec
   le passage entouré ; le même passage est surligné dans le texte à droite.
   Un fond **mauve** signale des mots produits par un modèle : vérifiez-les
   tous.
6. Inscrivez votre nom dans **Vérifié par** (il est retenu pour la prochaine
   fois) et, si utile, une **Remarque**.
7. Cliquez sur **Accepter**, **À retravailler** ou **Rejeter**. Le fichier
   suivant s'ouvre.

**Sans les PDF.** Cochez **Vérifier le texte seulement (sans PDF)** pour ne
faire que les contrôles qui n'ont pas besoin du PDF : texte répété en boucle,
mots brouillés, caractères mal décodés. Ils sont rapides, mais ils ne peuvent
pas repérer un passage bien écrit qui ne figure pas dans la source.

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
verbatim audit dossier_txt
```

`verbatim audit` mesure l'ensemble d'un corpus déjà converti et produit un
classement des fichiers les plus susceptibles d'être abîmés.
