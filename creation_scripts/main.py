import os, requests_cache, json, logging, re, shutil, math
from datetime import datetime as dt, timedelta as td
from PIL import Image
from pprint import pp
import makeHTML

# sets working directory to current folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# constants
GENS_FILTER = []
POKE_API_GENERATIONS_URL = "https://pokeapi.co/api/v2/generation/"
NAME_FORMATS = {
    "mr-mime": "Mr. Mime",
    "ho-oh": "Ho-oh",
    "mime-jr": "Mime Jr.",
    "porygon-z": "Porygon-Z",
    "type-null": "Type: Null",
    "red-meteor": "Meteor",
    "jangmo-o": "Jangmo-o",
    "hakamo-o": "Hakamo-o",
    "kommo-o": "Kommo-o",
    "amped-gmax": "Gigantamax",
    "mr-rime": "Mr. Rime",
    "wo-chien": "Wo-Chien",
    "chien-pao": "Chien-Poa",
    "ting-lu": "Ting-Lu",
    "chi-yu": "Chi-Yu",
    "": "Standard",
    "alola": "Alolan",
    "starter": "Partner",
    "galar": "Galarian",
    "gmax": "Gigantamax",
    "hisui": "Hisuian",
    "paldea": "Paldean",
}
HOME_IMAGES_DIRECTORY = "C:\\Users\\Kevin\\Pictures\\Pokemon\\HOME\\"
HOME_IMAGE_NAME = (
    "poke_capture_{natDex:04d}_{form:03d}_{gender}_{gmax}_{sweet:08d}_f_{shiny}.png"
)
OUTPUT_IMAGE_NAME = "{natDex:04d}_{formNum:03d}_{subform}_{species}{formName}"

# Database stores gender ratio.  -1 == genderless, 0 == male only, 8 == female only, 1-7 == the different rates.
# 9 being the "has gender differences" value is arbitrary but works well as it keeps all the unique states below 10.
# That way, the gendered form value can be 10 + gendered_only value, keeping them similar
# 1 is defined as both genders to avoid magic numbers, but any value not defined in the dictionary (namely 1-7) will return "mf"
GENDER_UNKNOWN = -1
GENDER_MALE_ONLY = 0
GENDER_BOTH = 1
GENDER_FEMALE_ONLY = 8
GENDER_HAS_DIMORPHISM = 9
GENDER_MALE_DIMORPHISM = GENDER_MALE_ONLY + 10
GENDER_FEMALE_DIMORPHISM = GENDER_FEMALE_ONLY + 10
IMAGE_GENDER = {
    GENDER_UNKNOWN: "uk",
    GENDER_MALE_ONLY: "mo",
    GENDER_BOTH: "mf",
    GENDER_FEMALE_ONLY: "fo",
    GENDER_MALE_DIMORPHISM: "md",
    GENDER_FEMALE_DIMORPHISM: "fd",
}

# Indeedee, Basculegion, and Oinkologne have dimorphism, but they're different variety, not forms
# skipping the female check for them avoids duplicates
GENDER_HAS_DIMORPHISM_BUT_ACTUALLY_DIFFERENT_VARIETIES = [876, 902, 916]

ARCEUS_FORM_REMAP = [0, 6, 16, 15, 12, 1, 9, 2, 7, 11, 4, 14, 3, 13, 5, 8, 10, None, 17]
KYUREM_FORM_REMAP = [0, 2, 1]
VIVILLON_FORM_REMAP = [6, 0, 1, 2, 3, 4, 5, 7, 8]
XERNEAS_FORM_REMAP = [1, 0]
ZYGARDE_FORM_REMAP = [0, None, None, 4, 1]
MAUSHOLD_FORM_REMAP = [1, 0]

FIND_PREVIOUS_SHINY = [774, 869]

IMAGE_GMAX = {True: "g", False: "n"}
IMAGE_OUTPUT_DIRECTORY = (
    "C:\\Users\\Kevin\\Documents\\Programs\\PokemonMarathon2\\images\\pokemon"
)
NORMAL_OUTPUT_DIRECTORY = os.path.join(IMAGE_OUTPUT_DIRECTORY, "normal")
SHINY_OUTPUT_DIRECTORY = os.path.join(IMAGE_OUTPUT_DIRECTORY, "shiny")
CUSTOM_IMAGE_DIRECTORY = "C:\\Users\\Kevin\\Documents\\Programs\\PokemonMarathon2\\creation_scripts\\custom_images"


# initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=os.path.join(
        os.getcwd(),
        "log.log",
    ),
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

# enables api requests with caching that expire after one week
session = requests_cache.CachedSession(expire_after=td(weeks=1))

# tracks which images are used
usedImages = set()


#
#
# MAIN FLOW
#
#
def formatName(input, speciesName="", dexNum=None):
    input = input.replace(speciesName, "").strip("-")

    output = NAME_FORMATS.get(
        input,
        " ".join(
            [NAME_FORMATS.get(word, word.capitalize()) for word in input.split("-")]
        ),
    )

    match dexNum:
        case 676:
            if output != "Natural":
                output += " Trim"
        case 898:
            if output != "Standard":
                output += " Rider"
        case 963:
            output += " Form"
        case dex if dex in [854, 855, 1012, 1013]:
            output = "Standard"
        case 1017:
            if output == "Standard":
                output = "Teal Mask"

    return output


def getFormGen(url):
    versionGroup = session.get(url).json()

    return session.get(versionGroup["generation"]["url"]).json()["id"]


def tryAllGenders(imageData):
    unusedGenders = IMAGE_GENDER.copy()
    unusedGenders.pop(imageData["gender"], None)

    for unusedGender in unusedGenders:
        imageData["gender"] = unusedGender
        image = findHomeImage(imageData)

        if image:
            return image

    return None


def resizeImage(imagePath):
    image = Image.open(imagePath)
    # custom images should be made with 256x256 versions, thumbnail() just exits if the new resolution is >= the current, so they won't be resized
    image.thumbnail((256, 256), Image.Resampling.LANCZOS)
    image.save(imagePath, "PNG")


def copyHomeImage(speciesName, formName, homeImageData):
    newImageName = OUTPUT_IMAGE_NAME.format(
        natDex=homeImageData["dex_num"],
        formNum=homeImageData["form_num"],
        subform=(
            "G"
            if homeImageData["gmax"]
            else "M" if homeImageData["mega"] else homeImageData["sweet"]
        ),
        # removing the period for a cleaner look and the colon was breaking Type: Null
        species=speciesName.replace(".", "").replace(":", "").replace(" ", "_"),
        formName="" if formName == "Standard" else "_" + formName.replace(" ", "_"),
    )

    normalOutputImage = os.path.join(NORMAL_OUTPUT_DIRECTORY, newImageName + ".png")
    shutil.copy(
        os.path.join(homeImageData["directory"], homeImageData["image_name"]),
        normalOutputImage,
    )
    resizeImage(normalOutputImage)

    shinyImageName = OUTPUT_IMAGE_NAME.format(
        natDex=homeImageData["dex_num"],
        formNum=homeImageData["form_num"],
        subform=(
            "G"
            if homeImageData["gmax"]
            else "M" if homeImageData["mega"] else homeImageData["sweet"]
        ),
        # removing the period for a cleaner look and the colon was breaking Type: Null
        species=speciesName.replace(".", "").replace(":", "").replace(" ", "_"),
        formName=(
            "_" + homeImageData["_shiny_form_name"].replace(" ", "_")
            if "_shiny_form_name" in homeImageData
            else "" if formName == "Standard" else "_" + formName.replace(" ", "_")
        ),
    )
    shinyOutputImage = os.path.join(SHINY_OUTPUT_DIRECTORY, shinyImageName + ".png")
    try:
        shutil.copy(
            os.path.join(
                homeImageData["directory"],
                "Shiny",
                re.sub(r"(?<=_)n(?=\.png)", "r", homeImageData["image_name"]),
            ),
            shinyOutputImage,
        )
        resizeImage(shinyOutputImage)
    except:
        shinyImageName = None

        if homeImageData["dex_num"] in FIND_PREVIOUS_SHINY:
            files = os.listdir(SHINY_OUTPUT_DIRECTORY)
            files.append(newImageName)
            files = sorted(files)
            previousShiny = files[files.index(newImageName) - 1]

            if newImageName[:4] == previousShiny[:4]:
                shinyImageName = previousShiny

    return {"image_name": newImageName, "shiny_image": shinyImageName}


def getHomeImageData(speciesData, varietyData, formData):
    return {
        "dex_num": speciesData["id"],
        "form_num": max(varietyData["_index"], formData["_index"]),
        "gmax": "gmax" in formData["form_name"],
        "mega": ("mega" in formData["form_name"] or "primal" in formData["form_name"]),
        "gender": formData["_gender"],
        "sweet": 0,
    }


def findHomeImage(imageData):
    # prevents changes to imageData from leaving this function unless explicitly returned
    imageData = imageData.copy()

    # controls where the image is obtained from the Home images repo or the custom images folder
    customImage = False

    # allow Urshifu to have multiple Gmaxes
    if imageData["gmax"] and imageData["dex_num"] != 892:
        imageData["form_num"] = 0

    # species specific checks
    match imageData["dex_num"]:
        # Pikachu
        case 25:
            match imageData["form_num"]:
                # skips Cosplays
                case form if form in range(1, 7):
                    return None
                # remaps Hats and Partner
                case form if form in range(7, 16):
                    imageData["form_num"] -= 6
                    # changes source directory form Partner to get custom image
                    if form == 14:
                        customImage = True
        # Eevee (changes source directory for Partner)
        case 133:
            match imageData["form_num"]:
                case 1:
                    customImage = True
        # Torchic (ensure both genders get processed despite only back images existing)
        case 255:
            imageData["gender"] = GENDER_MALE_DIMORPHISM
        # Arceus
        case 493:
            # skips unknown type
            if imageData["form_num"] == 17:
                return None
            # remaps actually existing types
            imageData["form_num"] = ARCEUS_FORM_REMAP[imageData["form_num"]]
        # Kyurem
        case 646:
            imageData["form_num"] = KYUREM_FORM_REMAP[imageData["form_num"]]
        # Vivillon
        case 666:
            # only the first 9 need to be changed, so if there's an index exception just keep the form
            try:
                imageData["form_num"] = VIVILLON_FORM_REMAP[imageData["form_num"]]
            except:
                pass
        # Xerneas
        case 716:
            imageData["form_num"] = XERNEAS_FORM_REMAP[imageData["form_num"]]
        # Zygarde
        case 718:
            if imageData["form_num"] in [1, 2]:
                return None
            imageData["form_num"] = ZYGARDE_FORM_REMAP[imageData["form_num"]]
        # Sinistea, Polteageist, Poltchageist, Sinistcha
        case dex if dex in [854, 855, 1012, 1013]:
            if imageData["form_num"] == 1:
                return None
        # Alcremie
        case 869:
            if not imageData["gmax"]:
                form = imageData["form_num"] % 9
                sweet = math.floor(imageData["form_num"] / 9)
                imageData["form_num"] = form
                imageData["sweet"] = sweet
        case 890:
            eternatus = True
        # Urshifu
        case 892:
            imageData["form_num"] %= 2
        # Maushold
        case 925:
            imageData["form_num"] = MAUSHOLD_FORM_REMAP[imageData["form_num"]]
        # Koraidon and Miraidon
        case dex if dex in [1007, 1008]:
            if imageData["form_num"] != 0:
                return None

    imageData["directory"] = (
        CUSTOM_IMAGE_DIRECTORY if customImage else HOME_IMAGES_DIRECTORY
    )

    imageData["image_name"] = HOME_IMAGE_NAME.format(
        natDex=imageData["dex_num"],
        form=imageData["form_num"],
        gender=IMAGE_GENDER.get(imageData["gender"], IMAGE_GENDER.get(GENDER_BOTH)),
        gmax=IMAGE_GMAX.get(imageData["gmax"]),
        sweet=imageData["sweet"],
        shiny="n",
    )

    imagePath = os.path.join(imageData["directory"], imageData["image_name"])
    if os.path.exists(imagePath):
        usedImages.add(imagePath)
        return imageData

    return None


def processMon(speciesData, varietyData, formData, imageData, homeImageData=None):
    if not homeImageData:
        homeImageData = findHomeImage(imageData)

        if not homeImageData:
            homeImageData = tryAllGenders(imageData)

    if not homeImageData:
        return None

    # reduces Minior's form number in the new image to skip the gaps caused by each color having its own meteor form
    if speciesData["id"] == 774 and imageData["form_num"] > 6:
        homeImageData["form_num"] = homeImageData["form_num"] % 7 + 1
        homeImageData["_shiny_form_name"] = "Core"

    # removes the cream from the name of Alcremie's shiny image
    if (
        speciesData["id"] == 869
        and homeImageData["form_num"] == 0
        and not homeImageData["gmax"]
    ):
        homeImageData["_shiny_form_name"] = formData["_formatted_name"][
            formData["_formatted_name"].index("Cream") + 6 :
        ]

    # makes Eternamax count as a gmax
    if speciesData["id"] == 890 and varietyData["_index"] == 1:
        homeImageData["gmax"] = True

    outputImageData = copyHomeImage(
        speciesData["_formatted_name"], formData["_formatted_name"], homeImageData
    )

    monData = {
        "Name": formData["_formatted_name"],
        "Image": outputImageData["image_name"],
        "Shiny": outputImageData["shiny_image"],
        "Gen": formData["_gen"],
        "Type A": formData["types"][0]["type"]["name"],
        "Type B": (
            None
            if len(formData["types"]) < 2
            else formData["types"][1]["type"]["name"]
        ),
        "HP": varietyData["stats"][0]["base_stat"],
        "Atk": varietyData["stats"][1]["base_stat"],
        "Def": varietyData["stats"][2]["base_stat"],
        "SpA": varietyData["stats"][3]["base_stat"],
        "SpD": varietyData["stats"][4]["base_stat"],
        "Spe": varietyData["stats"][5]["base_stat"],
        "BST": varietyData["_base_stat_total"],
    }

    if homeImageData["mega"]:
        monData["Mega"] = True
    if homeImageData["gmax"]:
        monData["Gmax"] = True

    return monData


def processForm(speciesData, varietyData, formIndex, form):
    formData = session.get(form["url"]).json()
    formData["_index"] = formIndex
    formData["_formatted_name"] = formatName(
        form["name"], speciesData["name"], speciesData["id"]
    )
    formData["_gender"] = speciesData["_gender"]
    formData["_gen"] = getFormGen(formData["version_group"]["url"])

    output = []

    # processes female form if gender dimorphism
    if (
        speciesData["_gender"] == GENDER_HAS_DIMORPHISM
        and speciesData["id"]
        not in GENDER_HAS_DIMORPHISM_BUT_ACTUALLY_DIFFERENT_VARIETIES
    ):
        formData["_gender"] = GENDER_FEMALE_DIMORPHISM
        femaleImage = findHomeImage(
            getHomeImageData(speciesData, varietyData, formData)
        )

        if femaleImage:
            formData["_formatted_name"] = formatName(
                formData["name"] + "-female", speciesData["name"]
            )
            output.append(
                processMon(
                    speciesData,
                    varietyData,
                    formData,
                    femaleImage,
                    femaleImage,
                )
            )

            formData["_formatted_name"] = formData["_formatted_name"].replace(
                "Female", "Male"
            )
            formData["_gender"] = GENDER_MALE_DIMORPHISM
        else:
            formData["_gender"] = GENDER_BOTH

    # skip Floette Eternal and Toxtricity Low Key Gmax
    if not (speciesData["id"] == 670 and varietyData["_index"] == 1) and not (
        speciesData["id"] == 849 and varietyData["_index"] == 3
    ):
        homeImageData = getHomeImageData(speciesData, varietyData, formData)
        output.insert(0, processMon(speciesData, varietyData, formData, homeImageData))

    return output


def processVariety(speciesData, varietyIndex, variety):
    varietyData = session.get(variety["pokemon"]["url"]).json()
    varietyData["_index"] = varietyIndex
    varietyData["_base_stat_total"] = sum(
        stat["base_stat"] for stat in varietyData["stats"]
    )

    return [
        mon
        for formIndex, form in enumerate(varietyData["forms"])
        for mon in processForm(speciesData, varietyData, formIndex, form)
        if mon is not None
    ]


def processSpecies(speciesURL):
    speciesData = session.get(speciesURL).json()
    speciesData["_formatted_name"] = formatName(speciesData["name"])
    speciesData["_gender"] = (
        GENDER_HAS_DIMORPHISM
        if speciesData["has_gender_differences"]
        else speciesData["gender_rate"]
    )

    return {
        "ID": speciesData["id"],
        "Species": speciesData["_formatted_name"],
        "Forms": [
            form
            for varietyIndex, variety in enumerate(speciesData["varieties"])
            for form in processVariety(speciesData, varietyIndex, variety)
            if form is not None
        ],
    }


def processGen(genURL):
    genData = session.get(genURL).json()

    return {
        "Gen": genData["id"],
        "Species": sorted(
            [processSpecies(species["url"]) for species in genData["pokemon_species"]],
            key=lambda species: species["ID"],
        ),
    }


def logUnusedImages():
    logger.warning("")
    logger.warning("CHECKING FOR MISSING FILES")
    logger.warning("")
    #    eggs, back, floette eternal, unused spidops, gendered mausholds, unused ogerpons
    ignoreThese = "(_0000_)|(_b_)|(_0670_005_)|(_0918_001_)|(_092[45]_00[01]_mf_)|(_1017_00[4-7])|(?!.png$)"
    for file in os.listdir(HOME_IMAGES_DIRECTORY):
        if re.search(ignoreThese, file):
            continue

        fullFile = os.path.join(HOME_IMAGES_DIRECTORY, file)
        if os.path.isfile(fullFile):
            if fullFile not in usedImages:
                logger.warning(f"FILE NOT USED: {fullFile}")


def clearImagesFolder():
    for file in os.listdir(NORMAL_OUTPUT_DIRECTORY):
        if file.endswith(".png"):
            os.remove(os.path.join(NORMAL_OUTPUT_DIRECTORY, file))

    for file in os.listdir(SHINY_OUTPUT_DIRECTORY):
        if file.endswith(".png"):
            os.remove(os.path.join(SHINY_OUTPUT_DIRECTORY, file))


if __name__ == "__main__":
    clearImagesFolder()

    startTime = dt.now()
    print(f"\nSTART: {startTime}")

    allGens = session.get(POKE_API_GENERATIONS_URL).json()["results"]
    gensToProcess = (
        [gen for (index, gen) in enumerate(allGens) if index + 1 in GENS_FILTER]
        if GENS_FILTER
        else allGens
    )

    allMonData = [processGen(gen["url"]) for gen in gensToProcess]

    endTime = dt.now()
    print(f"END: {endTime}")

    totalTime = (endTime - startTime).total_seconds()

    print(f"Completed in {totalTime} seconds\n")

    makeHTML.run(allMonData)

    with open(os.path.join(os.getcwd(), "output.json"), "w") as file:
        json.dump(allMonData, file, indent=2)
        file.close()

    logUnusedImages()

# TODO
# 1/6/25
# X Pikachu - 25 - hats = male only
# X Tauros - 128 - Paldean = male dimorphism
# X Torchic - 255 = male dimorphism
# X Greninja - 658 - Ash = male only
# X Meowstic - 678 = male only and female only
# X Alcremie - 869 = candy
# X Indeedee - 876 = male only and female only
# X Urshifu - 892 - rapid G = form 001
# X Ursaluna - 901 - blood moon = male only
# X Basculegion - 902 = male dimorphism form 000
# X Enamorous - 905 = female dimorphism
# X Oinkologne - 916 = male dimorphism form 000
# X Tinkatink, Tinkatuff, Tinkaton - 957, 958, 959 = female dimorphism
# X Koraidon, Miraidon - 1007, 1008 = skip form 001
# X Dipplin - 1011 = male female
# X Okidogi, Monkidori, Fezandipiti - 1014, 1015, 1016 = male only
# X Ogerpon - 1017 = female only (ensure form 004-007 aren't used)
# X Terapagos - 1024 - 000, 001, 002 = male female

# 1/7/25
# X Indeedee - there's four of them?

# 1/8/25
# X Pikachu - 25 - check hats
# X Quagsire, Buizel, Floatzel - 195, 418, 419 - gender difference back only?
# X Arceus - 493 - types wrong images
# X Kyurem, Vivillon, Xerneas, Zygarde, Necrozma, Alcremie - 646, 666, 716, 718, 800, 869 - images on wrong forms
# X Floette - 670 - eternal exists
# X Meowstic, Indeedee - 678, 876 - duplicate forms in output.json
# X Koraidon, Miraidon - 1007, 1008 - have multiple forms
# X Ogerpon - 1017 - Teal Mask labeled Original/Standard

# 1/10/25
# X missing if duplicate check added: 255 Torchic Male, 670 Floette Eternal, 849 Toxtricity Low Key Gmax, 892 Urshifu Rapid Strike Gmax, 902 Basculegion Male Male (female image), 916, Oinkologne Male Male (female image)

# 2/23/25
# X partner Pikachu and Eevee
# MISSING SHINIES:
# Pikachu - 25 - hats
# X Minior - 774 - not red
# X Aclremie - 869 - not gmax or vanilla cream
# Terapagos - 1024 - stellar
