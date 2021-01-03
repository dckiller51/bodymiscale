# bodymiscale

EN :

Hello at this stage this component is to be built. The purpose of this component is to have additional information when weighing yourself with a Miscale Xiaomi connected scale. Currently the weight is sent to Hassio with an ESPHOME. The calculator is the bodmiscale.py file. The database is in the user.yaml file we find name, weight, height, age, gender and impedance (only for miscale2). The sensor information.txt file corresponds to the attributes that we want generated in the sensor. The name of the sensor should be sensor.bodymiscale.username

FR : 

Bonjour à ce stade ce compossant est à construire. Le but de ce composant est d'avoir des informations supplémentaires lorsque l'on se pese avec une balance connectée Miscale Xiaomi. Actuellement le poids est envoyé sur Hassio avec un ESPHOME. Le calculateur est le fichier bodmiscale.py. La base de données est dans le fichier user.yaml on y retrouve name, le poids, la taille, l'age, le genre et l'impedance (uniquement pour la miscale2). Le fichier sensor information.txt correspond aux attributs que l'on souhaite généré dans le sensor. Le nom du sensor devra être sensor.bodymiscale.username

The generated data is :

## For miscale (181D)

- Weight
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label

## For miscale 2 (181B) (with to impedance)

- Weight
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label
- Lean body mass
- Body fat
- Water
- Bone mass
- Muscle mass
- Fat mass ideal
- Protein
- Body type
 
 ## Installation

- You can install it manually. Simply copy and paste the contents of the 
`bodymiscale/custom_components` folder in your` config/custom_components`. 
For example, you will get the file `__init __.Py` in the following path:
`/config/custom_components/bodymiscale/__init__. py`.

## Configuration
key | type | description
:--- | :--- | :---
**plateform (Required)** | string | `bodymiscale`
**name (Required)** | string | Custom name for the sensor. `bodymiscale.nom`
**weight (Required)** | sensors / sensor.weight_ | Your sensor returning your weight.
**impedance (Optional)** | sensors / sensor.impedance_ | Your sensor returning your impedance.
**height (Required)** | number | Your height in cm. 
**born (Required)** | string | Your birthday. `"1990-04-10"`
**gender (Required)** | string | female or male. `"male"` 

## Example
**Configuration YAML**
```yaml
bodymiscale: !include components/bodymiscale.yaml
```
Create a file in `/config/components/bodymiscale.yaml`.

**Configuration with default settings:**
```yaml
aurelien:
  sensors:
    weight: sensor.weight_aurelien
  height: 176
  born: "1990-04-10"
  gender: "male"
```
**Configuration with impedance (miscale2) settings:**
```yaml
aurelien:
  sensors:
    weight: sensor.weight_aurelien
	impedance: sensor.impedance_aurelien
  height: 176
  born: "1990-04-10"
  gender: "male"
```
