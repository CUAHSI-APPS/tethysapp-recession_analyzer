# Recession Analyzer

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)



## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
	- [Generator](#generator)
- [Badge](#badge)
- [Example Readmes](#example-readmes)
- [Related Efforts](#related-efforts)
- [Maintainers](#maintainers)
- [Contribute](#contribute)
- [License](#license)

## Background

Between rainfall events, watersheds enter a recession phase, during which stream flows (Q) decline. The rate of recession depends strongly on catchment physiographic features (e.g. landscape relief, or soil type), and has important consequences for availability of surface water for ecosystems and society. One common mathematical model used to describe the streamflow recession is the power law recession relationship.

 
![alt text](resources/plaw.png "Power law recession")


Parameters a and b can be fit to streamflow time series using one of many available methods (Brutsaert and Nieber, 1977; Wittenberg 1999; Biswal and Marani, 2010; Dralle et al., 2017). Recent research shows that values of a and b are highly variable, often changing depending on the particular mode of analysis used for identifying and fitting periods of recession from the hydrograph (Dralle et al., 2017). Differing from previous approaches, which sought to determine single, watershed-effective values for a and b, we here focus on estimating values of a and b from a collection of individual recession events identified using hydrograph analysis. For this purpose, we introduce the Recession Analyzer, designed to perform event-by-event power law recession analysis on daily United States Geological Survey (USGS) streamflow data. The app uses a collection of methodologies (Dralle et al., 2017) to extract recession segments from the hydrograph, and fit the power law recession model from Figure 1. The app also performs a statistical correction step outlined by Dralle et al. [2015] to remove scale dependence from the fitted collection of recession scale parameters, a. 


## Install

This project uses [node](http://nodejs.org) and [npm](https://npmjs.com). Go check them out if you don't have them locally installed.

```sh
$ npm install --global standard-readme-spec
```

## Usage

This is only a documentation package. You can print out [spec.md](spec.md) to your console:

```sh
$ standard-readme-spec
# Prints out the standard-readme spec
```

### Generator

To use the generator, look at [generator-standard-readme](https://github.com/RichardLitt/generator-standard-readme). There is a global executable to run the generator in that package, aliased as `standard-readme`.

## Badge

If your README is compliant with Standard-Readme and you're on GitHub, it would be great if you could add the badge. This allows people to link back to this Spec, and helps adoption of the README. The badge is **not required**.

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)

To add in Markdown format, use this code:

```
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)
```

## Example Readmes

To see how the specification has been applied, see the [example-readmes](example-readmes/).

## Related Efforts

- [Art of Readme](https://github.com/noffle/art-of-readme) - ð Learn the art of writing quality READMEs.
- [open-source-template](https://github.com/davidbgk/open-source-template/) - A README template to encourage open-source contributions.

## Maintainers

[@RichardLitt](https://github.com/RichardLitt).

## Contribute

Feel free to dive in! [Open an issue](https://github.com/RichardLitt/standard-readme/issues/new) or submit PRs.

Standard Readme follows the [Contributor Covenant](http://contributor-covenant.org/version/1/3/0/) Code of Conduct.

## License

[MIT](LICENSE) Â© Richard Littauer