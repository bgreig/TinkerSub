# Contributing to TinkerSub

TinkerSub is meant to be built, changed and improved. Here's how to share what you find.

## Ask a question or report a problem

Open an [issue](https://github.com/bgreig/TinkerSub/issues/new/choose) and pick the template that fits:

- **Build problem:** something doesn't fit, print or work as the guide says.
- **Part sourcing:** a part is hard to find, discontinued, or you found a better source.
- **Design change:** an idea for the next version.

Include the part number (the three digits debossed on every printed part), the guide section, and a photo if you can. Photos solve most build questions in one go.

## Share a build or a modification

Add it to the [wiki](https://github.com/bgreig/TinkerSub/wiki): the Build log for photos and notes, Modifications for changes you made and tested, Parts sourcing for where you bought things.

## Change the design files

1. Fork the repository and make a branch.
2. Change the generator in `Source/` (see `Source/README.md` for which file makes which part), not the STL by hand. Exported STLs and STEPs drift from the source and get overwritten on the next build.
3. Rebuild with `python3 Source/build.py all`, read the list of changed files it prints, then `python3 Source/build.py install`. The `parts` step must report `v6 interferences: none` and pass the fastener check (every screw hole followed through the assembled model; it stops the build on any problem), and `checks/print_review.py` should show nothing new for your part. If you add or move a screw, add it to `Source/assembly/fasteners.py`.
4. Open a pull request that says what you changed, why, and whether you've printed or built it. Say so if you haven't.

Firmware changes: run the host tests in `Firmware/test` before sending them (see `Firmware/README.md`).

## Keep it safe

Changes that touch the pressure hull, the battery, the fuses or the 12 V wiring need to say how they were tested. A leak or a battery fault does more damage than any other failure on this vehicle.

## License

By contributing you agree that your contribution is licensed like the rest of the project: hardware under CERN-OHL-S-2.0, software under MIT, documentation under CC BY-SA 4.0.
