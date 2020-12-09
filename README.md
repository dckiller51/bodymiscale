# bodymiscale
 
 Bonjour à ce stade ce compossant est à construire. Le but de ce composant est d'avoir des informations supplémentaires lorsque l'on se pese avec une balance connectée Miscale Xiaomi.
 Actuellement le poids est envoyé sur Hassio avec un ESPHOME. Le calculateur est le fichier bodmiscale.py. 
 La base de données est dans le fichier user.yaml on y retrouve  username, le poids, la taille, l'age, le genre et l'impedance (uniquement pour la miscale2). 
 Le fichier sensor information.txt correspond aux attributs que l'on souhaite généré dans le sensor. Le nom du sensor devra être sensor.bodymiscale.username.

Les données sont :

Pour miscale

- Weight
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label

Pour miscale 2 (gràce à l'impedance)

- Weight
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label
- Lean_body_mass
- Body fat
- Water
- Bone mass
- Muscle mass
- Protein
- Body type
- Metabolic age 
 
 
