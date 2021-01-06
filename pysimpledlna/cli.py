from . import dlna

import pkgutil


def main():
    # only for test
    data = pkgutil.get_data("pysimpledlna", "templates/action-{0}.xml".format('Play'))
    print(data)
    action_data = pkgutil.get_data("pysimpledlna", "templates/action-{0}.xml".format('Play')).decode("UTF-8")
    print(action_data)

if __name__ == "__main__":
    main()