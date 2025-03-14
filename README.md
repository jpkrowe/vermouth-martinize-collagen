# Martinize2 and vermouth: The ultimate resolution transformation tools

[![Build Status](https://github.com/marrink-lab/vermouth-martinize/actions/workflows/run_tests.yml/badge.svg)](https://github.com/marrink-lab/vermouth-martinize/actions)
[![codecov](https://codecov.io/gh/marrink-lab/vermouth-martinize/branch/master/graph/badge.svg)](https://codecov.io/gh/marrink-lab/vermouth-martinize)
[![Documentation Status](https://readthedocs.org/projects/vermouth-martinize/badge/?version=latest)](https://vermouth-martinize.readthedocs.io/en/latest/?badge=latest)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7361701.svg)](https://doi.org/10.5281/zenodo.7361701)
[![arXiv](https://img.shields.io/badge/arXiv-2105.05890-b31b1b.svg)](http://arxiv.org/abs/2212.01191)

This program is a slight modification of martinize2 in which new parameters for collagen are included. These include HYP parameters in the AMBER force field files and martini 3 bonded parameters.

Martinize2 is a rewrite of [Martinize]. It is aimed at producing
coarse-grained structures and topologies from an atomistic structure. Martinize
is primarily developed for the [Martini] coarse-grained force field and the
[Gromacs] simulation engine. However the architecture of the program will
allow us to support a broader range of force fields and simulation engines in
the future.

Vermouth (for VERsatile, MOdular,  and Universal Tranformation Helper) is the
python library that powers Martinize2. It allows to describe and apply
transformation on molecular structures and topologies using graph algorithms.

## Disclaimer

Martinize2 and Vermouth are under development. So far they have mostly been
tested on Martini 2 and Martini 3. If you use Martinize 2 and Vermouth for any
other force field be sure to carefully check the resulting topologies!  
Bugs can occur. If you encounter an issue, please report it on
<https://github.com/marrink-lab/vermouth-martinize/issues>. Carefully check your
 input and output files before using them; read the messages displayed by the
 program.

## Installation

Martinize2 and vermouth require python 3.9 or greater. They are distributed via [PyPi][pypi_vermouth], and can be
installed using the `pip` command:
    
    pip install vermouth

This installs the last released version. You can update an existing installation by running `pip install -U vermouth`.
In some cases you may want to experiment with running the latest development version. You can install this version with
the following command: 

    pip install git+https://github.com/jpkrowe/vermouth-martinize-collagen.git#vermouth

Note that vermouth and Martinize2, in particular development versions, may contain bugs that cause it to produce
incorrect topologies. Check the produced output carefully!

Martinize2 and vermouth have [mdtraj][mdtraj] as optional dependency as an 
alternative to dssp.

The behavior of the `pip` command can vary depending of the specificity of your
python installation. See the [documentation on installing a python
package][pipdoc] to learn more.

## Basic usage

Installing Martinize2 and vermouth with `pip` adds the `martinize2` program to
the research PATH. You can see the available option of the program by running:

    martinize2 -h

At the moment, martinize2 tries to reproduce the interface of the original
Martinize. You can find explanations on how to use Martinize on the [Martini
tutorials]; in most cases, replacing calls to `martinize.py` by calls to
`martinize2` should produce similar results.

The documentation of the vermouth python library will come soon.

## Citation
```
@article{kroon2022martinize2,
  title={Martinize2 and Vermouth: Unified Framework for Topology Generation},
  author={Kroon, Peter C and Gr{\"u}newald, Fabian and Barnoud, Jonathan and van Tilburg, Marco 
          and Souza, Paulo CT and Wassenaar, Tsjerk A and Marrink, Siewert-Jan},
  journal={arXiv preprint arXiv:2212.01191},
  year={2022}}
```

## Documentation

More complete documentation, including API documentation can be found at
https://vermouth-martinize.readthedocs.io/

## License

Martinize2 and vermouth are distributed under the Apache 2.0 license.

    Copyright 2018 University of Groningen

	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at

		http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.

The [full text of the license][license] is available in the source repository.

## Contributions

The development of Martinize2 and vermouth is done on [github]. Contributions
are welcome as [bug reports] and [pull requests]. Note however that the
decision of whether or not contributions can give authorship on the resulting
academic paper is left to our sole discretion.

[Martinize]: https://github.com/Tsjerk/Martinize
[Martini]: http://cgmartini.nl
[Martini tutorials]: http://cgmartini.nl/index.php/tutorials-general-introduction-gmx5
[Gromacs]: http://www.gromacs.org
[pypi_vermouth]: https://pypi.org/project/vermouth/
[mdtraj]: https://www.mdtraj.org/
[pipdoc]: https://packaging.python.org/tutorials/installing-packages/#installing-packages
[license]: https://github.com/marrink-lab/vermouth-martinize/blob/master/LICENSE
[github]: https://github.com/marrink-lab/vermouth-martinize
[bug reports]: https://github.com/marrink-lab/vermouth-martinize/issues
[pull requests]: https://github.com/marrink-lab/vermouth-martinize/pulls
