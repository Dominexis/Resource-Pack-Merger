# Import things

import shutil
import json
import sys
from pathlib import Path



# Check that correct Python version is running

if not (
    (sys.version_info[0] == 3 and sys.version_info[1] >= 9)
    or
    (sys.version_info[0] > 3)
):
    print("\n\n ERROR: Resource Pack Merger requires Python 3.9 or newer!")
    input()
    exit()



# Initialize variables

PROGRAM_PATH = Path(__file__).parent
OUTPUT_PACK = PROGRAM_PATH / "Dom's Nexus RP - By Dominexis" / "assets"
PACK_FORMAT = 12
NEXUS_VERSION = "2.0.0"



# Define functions

def program():
    """The main function of the program.
    Having everything run in functions prevents things from running globally which isn't always desired."""
    delete_existing_pack()
    pack_list = get_pack_list()
    create_pack_mcmeta()
    output_pack_list = merge_packs(pack_list)
    create_constituent_pack_file(output_pack_list)

    print("\nResource pack merging complete")
    input()

def delete_existing_pack():
    """Deletes the existing output resource pack to start from scratch."""
    if OUTPUT_PACK.exists():
        shutil.rmtree(OUTPUT_PACK)

def get_pack_list() -> list[str]:
    """Gets the list of resource packs to merge together."""
    file_path = PROGRAM_PATH / "Resource Pack Merger Input.txt"
    if not file_path.exists():
        print("ERROR: 'Resource Pack Merger Input.txt' does not exist!")
        input()
        exit()
    with file_path.open("r", encoding="utf-8") as file:
        return file.read().split("\n")

def create_pack_mcmeta():
    """Creates the `pack.mcmeta` file in the output resource pack."""
    path = PROGRAM_PATH / "Dom's Nexus RP - By Dominexis"
    path.mkdir(exist_ok=True)
    with (path / "pack.mcmeta").open("w", encoding="utf-8") as file:
        json.dump(
            {
                "pack": {
                    "pack_format": PACK_FORMAT,
                    "description": [
                        "",
                        { "text": "Dom's Nexus", "color": "blue", "bold": True },
                        "\n",
                        { "text": "By ", "color": "gray" },
                        { "text": "Dominexis", "color": "blue" },
                        { "text": " - ", "color": "gray" },
                        { "text": f"{NEXUS_VERSION}+", "color": "gold" }
                    ]
                }
            },
            file,
            indent=4
        )

def merge_packs(pack_list: list[str]) -> list[str]:
    """Iterates through the constituent resource packs and merges them together."""
    output_pack_list = ["List of constituent packs:\n"]

    # Iterate through resource packs
    for pack in pack_list:
        if pack == "":
            continue

        pack_path = PROGRAM_PATH / pack / "assets"
        if not pack_path.exists():
            print(f"ERROR: {pack} doesn't exist!")
            continue

        output_pack_list.append(pack)
        merge_pack(pack, pack_path)

    return output_pack_list

def merge_pack(pack: str, pack_path: Path):
    """Merges a single resource pack into the output resource pack."""
    print(f"Merging {pack}")

    # Iterate through files in resource pack
    for file_path in pack_path.glob("**/*"):
        if file_path.is_dir():
            continue

        # Get pack subdirectory folder list
        pack_subdir = file_path.as_posix()[len(pack_path.as_posix())+1:]
        folders = pack_subdir.split("/")

        merge_file(file_path, OUTPUT_PACK / pack_subdir, folders)

def merge_file(file_path: Path, output_file_path: Path, folders: list[str]):
    """Merges a single file into the output resource pack."""
    # Create output folder directory
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file if it doesn't exist in the destination
    if not output_file_path.exists():
        shutil.copy(file_path, output_file_path)
        return

    # Merge contents of files based on directory
    if len(folders) >= 3 and folders[0:3] == ["minecraft", "models", "item"]:
        merge_item_model(file_path, output_file_path)
        return
    if len(folders) == 2 and file_path.name == "sounds.json":
        merge_arbitrary_json(file_path, output_file_path)
        return
    if len(folders) >= 2 and folders[1] == "lang":
        merge_arbitrary_json(file_path, output_file_path)
        return
    if len(folders) >= 2 and folders[0:2] == ["minecraft", "atlases"]:
        merge_arbitrary_json_list(file_path, output_file_path, "sources")
        return
    if len(folders) >= 2 and folders[1] == "font":
        merge_arbitrary_json_list(file_path, output_file_path, "providers")
        return

    # Overwrite file otherwise
    shutil.copy(file_path, output_file_path)

def merge_item_model(file_path: Path, output_file_path: Path):
    """Merges the input item model JSON into the output item model JSON.\n
    Merging item models together requires special care as the custom model data must be preserved,
    and sorted in ascending order in the overrides list."""
    new_contents, load_bool = open_json(file_path)
    if not load_bool:
        return
    existing_contents, load_bool = open_json(output_file_path)
    if not load_bool:
        shutil.copy(file_path, output_file_path)
        return

    # Extract overrides from new contents
    if "overrides" not in new_contents:
        return
    new_overrides: list[dict] = new_contents["overrides"]

    # Merge overrides if overrides exist in the existing contents
    if "overrides" in existing_contents:
        existing_contents["overrides"] = merge_overrides(existing_contents["overrides"], new_overrides)

    # Put overrides directly into existing contents if they don't exist
    else:
        existing_contents["overrides"] = new_overrides

    # Save contents to existing file
    with output_file_path.open("w", encoding="utf-8") as file:
        json.dump(existing_contents, file, indent=4)

def merge_overrides(existing_overrides: list[dict], new_overrides: list[dict]) -> list[dict]:
    """Merge together the overrides from a particular item model into the output item model.\n
    Merging item models together requires special care as the custom model data must be preserved,
    and sorted in ascending order in the overrides list."""
    # Iterate through new overrides
    for new_override in new_overrides:

        # Get custom model data value
        if "predicate" in new_override and "custom_model_data" in new_override["predicate"]:
            new_custom_model_data: int = new_override["predicate"]["custom_model_data"]

            # Iterate through existing overrides
            for i in range(len(existing_overrides)):
                existing_override = existing_overrides[i]

                # Insert it if the custom model data is larger
                if not ("predicate" in existing_override and "custom_model_data" in existing_override["predicate"]):
                    continue
                existing_custom_model_data: int = existing_override["predicate"]["custom_model_data"]
                if new_custom_model_data <= existing_custom_model_data:
                    existing_overrides.insert(i, new_override)
                    break

            # Insert it at the end if none of them are larger
            else:
                existing_overrides.append(new_override)
        else:
            # Put override at the end
            existing_overrides.append(new_override)

    return existing_overrides

def merge_arbitrary_json(file_path: Path, output_file_path: Path):
    """Merges together arbitrary JSON files."""
    new_contents, load_bool = open_json(file_path)
    if not load_bool:
        return
    existing_contents, load_bool = open_json(output_file_path)
    if not load_bool:
        shutil.copy(file_path, output_file_path)
        return

    # Merge contents together
    key: str
    for key in new_contents:
        existing_contents[key] = new_contents[key]

    # Save contents to existing file
    with output_file_path.open("w", encoding="utf-8") as file:
        json.dump(existing_contents, file, indent=4)

def merge_arbitrary_json_list(file_path: Path, output_file_path: Path, list_key: str):
    """Merges a particular list inside a JSON file into the same list in the output JSON file.
    This is used for things like atlases and fonts that contain a list of entries
    that need to be merged together and not overwritten."""
    new_contents, load_bool = open_json(file_path)
    if not load_bool:
        return
    existing_contents, load_bool = open_json(output_file_path)
    if not load_bool:
        shutil.copy(file_path, output_file_path)
        return

    # Extract elements from new contents
    if list_key not in new_contents:
        return
    new_elements: list = new_contents[list_key]
        
    # Merge elements if elements exist in the existing contents
    if list_key in existing_contents:
        for element in new_elements:
            if element not in existing_contents[list_key]:
                existing_contents[list_key].append(element)

    # Put elements directly into existing contents if they don't exist
    else:
        existing_contents[list_key] = new_elements

    # Save contents to existing file
    with output_file_path.open("w", encoding="utf-8") as file:
        json.dump(existing_contents, file, indent=4)



def open_json(file_path: Path) -> tuple[dict, bool]:
    """Safely opens up JSON files and returns an error if it is formatted incorrectly.\n
    The built-in JSON library doesn't handle certain encoding schemes properly,
    so this function is used to ensure the correct encoding is used."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.loads(file.read().encode(encoding="utf-8", errors="backslashreplace")), True
    except (json.JSONDecodeError, FileNotFoundError):
        print(f'ERROR: Invalid JSON file at: {file_path.as_posix()[len(PROGRAM_PATH.as_posix())+1:]}')
        return {}, False



def create_constituent_pack_file(output_pack_list: list[str]):
    """Creates the text file containing the list of resource packs which were used to create the output."""
    with (PROGRAM_PATH / "Dom's Nexus RP - By Dominexis" / "Constituent Packs.txt").open("w", encoding="utf-8") as file:
        file.write("\n".join(output_pack_list))



# Run function

if __name__ == "__main__":
    program()