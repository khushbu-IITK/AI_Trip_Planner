## this is setup.py file which is used to install the dependencies of the project
## so that each module can be imported in any file of the project without any error or without much module importing....

### it is being installed using pip install -e . command in the terminal of the project folder and the -e .is added to the requirements.txt file to avoid any error while installing the dependencies of the project.
from setuptools import find_packages,setup
from typing import List

def get_requirements()->List[str]:
    """
    This function will return list of requirements
    """
    requirement_list:List[str] = []
    
    try:
        # Open and read the requirements.txt file
        with open('requirements.txt', 'r') as file:
            # Read lines from the file
            lines = file.readlines()
            # Process each line
            for line in lines:
                # Strip whitespace and newline characters
                requirement = line.strip()
                # Ignore empty lines and -e .
                if requirement and requirement != '-e .':
                    requirement_list.append(requirement)
    except FileNotFoundError:
        print("requirements.txt file not found.")

    
        
    return requirement_list
print(get_requirements())

setup(
    name="AI-TRAVEL-PLANNER",
    version="0.0.1",
    author="sunny savita",
    author_email="snshrivas3365@gmail.com",
    packages = find_packages(),
    install_requires=get_requirements()
)