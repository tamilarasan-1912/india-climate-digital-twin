from pathlib import Path
import xarray as xr


DATA_DIR = Path("backend/data")


def find_netcdf_files():
    files = []

    for pattern in ["*.nc", "*.nc4", "*.netcdf"]:
        files.extend(DATA_DIR.rglob(pattern))

    return files


def inspect_file(path: Path):
    print("=" * 70)
    print("FILE:", path)
    print("=" * 70)

    try:
        dataset = xr.open_dataset(path)

        print("\nDATASET:")
        print(dataset)

        print("\nDIMENSIONS:")
        for name, size in dataset.sizes.items():
            print(f"  {name}: {size}")

        print("\nCOORDINATES:")
        for name in dataset.coords:
            print(f"  {name}")

        print("\nDATA VARIABLES:")
        for name in dataset.data_vars:
            variable = dataset[name]

            print(f"\n  Variable: {name}")
            print(f"  Dimensions: {variable.dims}")
            print(f"  Shape: {variable.shape}")

            if "units" in variable.attrs:
                print(
                    f"  Units: {variable.attrs['units']}"
                )

            if "long_name" in variable.attrs:
                print(
                    f"  Description: "
                    f"{variable.attrs['long_name']}"
                )

        print("\nGLOBAL ATTRIBUTES:")

        for key, value in dataset.attrs.items():
            print(f"  {key}: {value}")

        dataset.close()

    except Exception as error:
        print("\nERROR:")
        print(error)


def main():
    files = find_netcdf_files()

    if not files:
        print("=" * 70)
        print("NO NETCDF FILE FOUND")
        print("=" * 70)
        print()
        print(
            "Place the IMD NetCDF file inside:"
        )
        print()
        print("backend/data/")
        print()
        return

    print(
        f"Found {len(files)} NetCDF file(s)."
    )

    for file in files:
        inspect_file(file)


if __name__ == "__main__":
    main()
