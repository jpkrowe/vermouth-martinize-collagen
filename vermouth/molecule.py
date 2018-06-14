# -*- coding: utf-8 -*-
# Copyright 2018 University of Groningen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Created on Thu Sep 14 10:58:04 2017

@author: Peter Kroon
"""

from collections import defaultdict, OrderedDict, namedtuple
import copy
from functools import partial
import itertools

import networkx as nx
import numpy as np

from . import graph_utils
from . import geometry


Interaction = namedtuple('Interaction', 'atoms parameters meta')
DeleteInteraction = namedtuple('DeleteInteraction',
                               'atoms atom_attrs parameters meta')


class LinkPredicate:
    """
    Comparison criteria for node and molecule attributes in links.

    When comparing an attribute from a link to a corresponding attribute from
    a molecule or a molecule node, the default behavior is to use the equality
    as criterion for the correspondence. Some correspondence, however must be
    broader for the link to be usable. Such alternative criteria are defined
    as link predicates.

    If an attribute in a link is set to an instance of a predicate, then the
    correspondence is defined as the boolean result of the ``match`` method.

    This is the base class for such predicate. It must be subclassed, and
    subclasses must define a :meth:`match` method that takes a dictionary and
    a potential key from that dictionary as arguments.

    Parameters
    ----------
    value:
        The per-instance value that serve as reference. How this value is
        treated depends on the subclass.
    """
    def __init__(self, value):
        self.value = value

    def match(self, node, key):
        """
        Do the comparison with the reference value.

        Notes
        -----
        This function **must** be defined by the subclasses. This docstring
        describe the *expected* format of the method.

        Parameters
        ----------
        node: dict
            A dictionary of attributes in which to look up. This can be a
            node dictionary of a molecule ``meta`` attribute.
        key:
            A potential key from the ``node`` dictionary.

        Returns
        -------
        bool
        """
        
        raise NotImplementedError

    def __repr__(self):
        return '<{} at {:x} value={}>'.format(self.__class__.__name__, id(self), self.value)


class Choice(LinkPredicate):
    """
    Test if an attribute is defined and in a predefined list.

    Parameters
    ----------
    value: list
        The list of value in which to look for the attribute.
    """
    def match(self, node, key):
        """
        Apply the comparison.
        """
        return node.get(key) in self.value


class NotDefinedOrNot(LinkPredicate):
    """
    Test if an attribute is not the reference value.

    This test passes if the attribute is not defined, if it is set to ``None``,
    or if its value is different from the reference.

    Notes
    -----
    If the reference is set to ``None``, then the test does not pass if the
    attribute is explicitly set to ``None``. It still passes if the attribute
    is not defined.

    Parameters
    ----------
    value:
        The value the attribute is tested not to be.
    """
    def match(self, node, key):
        """
        Apply the comparison.
        """
        return key not in node or node[key] != self.value


class LinkParameterEffector:
    """
    Rule to calculate an interaction parameter in a link.

    This class allows to store dynamic parameters in link interactions. The
    value of the parameter can be computed from the graph using the node keys
    given when creating the instance.

    An instance of this class is first initialized with a list of node keys
    from the link in which it is defined. The instance is latter called
    like a function, and takes as arguments a molecule and a match dictionary
    linking the link nodes with the molecule ones. The format of the dictionary
    is expected to be ``{link key: molecule key}``.

    An instance can also have a format defined. If defined, that format will be
    applied to the value computed by the :meth:`_apply` method causing the
    output to be a string. The format is given as a 'format_spec' from the
    python format string syntax. This format spec corresponds to what follows
    the column the column in string templates. For instance, formating a
    floating number to have 2 decimal places will be obtained by setting format
    to `.2f`. If no format is defined, then the calculated value is not
    modified.

    This is a base class; it needs to be subclassed. A subclass must define an
    :meth:`_apply` method that takes a molecule and a list of node keys from
    that molecule as arguments. This method is not called directly by the user,
    instead it is called by the :meth:`__call__` method when the user calls the
    instance as a function. A subclass can also set the :attr:`n_keys_asked`
    class attribute to the number of required keys. If the
    attribute is set, then the number of keys provided when initializing a new
    instance will be validated against that number; else, the user can pass an
    arbitrary number of keys without validation.
    """
    n_keys_asked = None

    def __init__(self, keys, format=None):
        """
        Parameters
        ----------
        keys: list
            A list of node keys from the link. If the :attr:`n_keys_asked`
            class argument is set, the number of keys must correspond to the
            value of the attribute.
        format: str
            Format specification.

        Raises
        ------
        ValueError
            Raised if the :attr:`n_keys_asked` class attribute is set and the
            number of keys does not correspond.
        """
        self.keys = keys
        if self.n_keys_asked is not None and len(self.keys) != self.n_keys_asked:
            raise ValueError(
                'Unexpected number of keys provided in {}: '
                '{} were expected, but {} were provided.'
                .format(self.__class__.name, self.n_keys_asked, len(keys))
            )
        self.format = format

    def __call__(self, molecule, match):
        """
        Parameters
        ----------
        molecule: Molecule
            The molecule from which to calculate the parameter value.
        match: dict
            The correspondence between the nodes from the link (keys), and the
            nodes from the molecule (values).

        Returns
        -------
        value:
            The calculated parameter value, formatted if required.
        """
        keys = [match[key] for key in self.keys]
        result = self._apply(molecule, keys)
        if self.format is not None:
            result = '{value:{format}}'.format(value=result, format=self.format)
        return result

    def _apply(self, molecule, keys):
        """
        Calculate the parameter value from the molecule.

        Notes
        -----
        This method **must** be defined in a subclass.

        Parameters
        ----------
        molecule: Molecule
            The molecule from which to compute the parameter value.
        keys: list
            A list of keys to use from the molecule.

        Returns
        -------
        value:
            The value for the parameter.
        """
        msg = 'The method need to be implemented by the children class.'
        raise NotImplementedError(msg)


class ParamDistance(LinkParameterEffector):
    """
    Calculate the distance between a pair of nodes.
    """
    n_keys_asked = 2

    def _apply(self, molecule, keys):
        # This will raise a ValueError if an atom is missing, or if an
        # atom does not have position.
        positions = np.stack([molecule.nodes[key]['position'] for key in keys])
        # We assume there are two rows; which we can since we checked earlier
        # that exactly two atom keys were passed.
        distance = np.sqrt(np.sum(np.diff(positions, axis=0)**2))
        return distance


class ParamAngle(LinkParameterEffector):
    """
    Calculate the angle in degrees between three consecutive nodes.
    """
    n_keys_asked = 3

    def _apply(self, molecule, keys):
        # This will raise a ValueError if an atom is missing, or if an
        # atom does not have position.
        positions = np.stack([molecule.nodes[key]['position'] for key in keys])
        vectorBA = positions[0, :] - positions[1, :]
        vectorBC = positions[2, :] - positions[1, :]
        angle = geometry.angle(vectorBA, vectorBC)
        return np.degrees(angle)


class ParamDihedral(LinkParameterEffector):
    """
    Calculate the dihedral angle in degrees defined by four nodes.
    """
    n_keys_asked = 4

    def _apply(self, molecule, keys):
        # This will raise a ValueError if an atom is missing, or if an
        # atom does not have position.
        positions = np.stack([molecule.nodes[key]['position'] for key in keys])
        angle = geometry.dihedral(positions)
        return np.degrees(angle)


class ParamDihedralPhase(LinkParameterEffector):
    """
    Calculate the dihedral angle in degrees defined by four nodes shifted by -180 degrees.
    """
    n_keys_asked = 4

    def _apply(self, molecule, keys):
        # This will raise a ValueError if an atom is missing, or if an
        # atom does not have position.
        positions = np.stack([molecule.nodes[key]['position'] for key in keys])
        angle = geometry.dihedral_phase(positions)
        return np.degrees(angle)


class Molecule(nx.Graph):
    # As the particles are stored as nodes, we want the nodes to stay
    # ordered.
    node_dict_factory = OrderedDict

    def __init__(self, *args, **kwargs):
        self.meta = kwargs.pop('meta', {})
        self._force_field = kwargs.pop('force_field', None)
        self.nrexcl = kwargs.pop('nrexcl', None)
        super().__init__(*args, **kwargs)
        self.interactions = defaultdict(list)

    @property
    def force_field(self):
        """
        The force field the molecule is described for.

        The force field is assumed to be consistent for all the molecules of
        a system. While it is possible to reassign
        :attr:`Molecule._force_field`, it is recommended to assign the force
        field at the system level as reassigning :attr:`System.force_field`
        will propagate the change to all the molecules in that system.
        """
        return self._force_field

    @property
    def atoms(self):
        for node in self.nodes():
            node_attr = self.node[node]
            yield node, node_attr

    def copy(self, as_view=False):
        copy = super().copy(as_view)
        if not as_view:
            copy = self.__class__(copy)
        copy._force_field = self.force_field
        copy.meta = self.meta.copy()
        return copy

    def subgraph(self, *args, **kwargs):
        return self.__class__(super().subgraph(*args, **kwargs))

    def add_interaction(self, type_, atoms, parameters, meta=None):
        if meta is None:
            meta = {}
        for atom in atoms:
            if atom not in self:
                # KeyError?
                raise ValueError('Unknown atom {}'.format(atom))
        self.interactions[type_].append(
            Interaction(atoms=tuple(atoms), parameters=parameters, meta=meta)
        )

    def add_or_replace_interaction(self, type_, atoms, parameters, meta=None):
        if meta is None:
            meta = {}
        for idx, interaction in enumerate(self.interactions[type_]):
            if (interaction.atoms == tuple(atoms)
                    and interaction.meta.get('version', 0) == meta.get('version', 0)):
                new_interaction = Interaction(
                    atoms=tuple(atoms), parameters=parameters, meta=meta,
                )
                self.interactions[type_][idx] = new_interaction
                break
        else:  # no break
            self.add_interaction(type_, atoms, parameters, meta)

    def get_interaction(self, type_):
        return self.interactions[type_]

    def remove_interaction(self, type_, atoms, version=0):
        for idx, interaction in enumerate(self.interactions[type_]):
            if interaction.atoms == atoms and interaction.meta.get('version', 0):
                break
        else:  # no break
            msg = ("Can't find interaction of type {} between atoms {} "
                   "and with version {}")
            raise KeyError(msg.format(type_, atoms, version))
        del self.interactions[type_][idx]

    def remove_matching_interaction(self, type_, template_interaction):
        for idx, interaction in enumerate(self.interactions[type_]):
            if interaction_match(self, interaction, template_interaction):
                del self.interactions[type_][idx]
                break
        else:  # no break
            raise ValueError('Cannot find a matching interaction.')

    def find_atoms(self, **attrs):
        for node_idx in self:
            node = self.nodes[node_idx]
            if all(node.get(attr, None) == val for attr, val in attrs.items()):
                yield node_idx

    def __getattr__(self, name):
        # TODO: DRY
        if name.startswith('get_') and name.endswith('s'):
            type_ = name[len('get_'):-len('s')]
            return partial(self.get_interaction, type_)
        elif name.startswith('add_'):
            type_ = name[len('add_'):]
            return partial(self.add_interaction, type_)
        elif name.startswith('remove_'):
            type_ = name[len('remove_'):]
            return partial(self.remove_interaction, type_)
        else:
            raise AttributeError('Unknown attribute "{}".'.format(name))

    def merge_molecule(self, molecule):
        """
        Add the atoms and the interactions of a molecule at the end of this one.

        Atom and residue index of the new atoms are offset to follow the last
        atom of this molecule.

        Parameters
        ----------
        molecule: Molecule
            The molecule to merge at the end.
        """
        if self.force_field != molecule.force_field:
            raise ValueError(
                'Cannot merge molecules with different force fields.'
            )
        if self.nrexcl is None and not self:
            self.nrexcl = molecule.nrexcl
        if self.nrexcl != molecule.nrexcl:
            raise ValueError(
                'Cannot merge molecules with different nrexcl. '
                'This molecule has nrexcl={}, while the other has nrexcl={}.'
                .format(self.nrexcl, molecule.nrexcl)
            )
        if len(self.nodes()):
            # We assume that the last id is always the largest.
            last_node_idx = max(self) 
            offset = last_node_idx
            residue_offset = self.nodes[last_node_idx]['resid']
            offset_charge_group = self.nodes[last_node_idx].get('charge_group', 1)
        else:
            offset = 0
            residue_offset = 0
            offset_charge_group = 0
        correspondence = {}
        for idx, node in enumerate(molecule.nodes(), start=offset + 1):
            correspondence[node] = idx
            new_atom = copy.copy(molecule.nodes[node])
            new_atom['resid'] = (new_atom.get('resid', 1) + residue_offset)
            new_atom['charge_group'] = (new_atom.get('charge_group', 1)
                                        + offset_charge_group)
            self.add_node(idx, **new_atom)
        for name, interactions in molecule.interactions.items():
            for interaction in interactions:
                atoms = tuple(correspondence[atom] for atom in interaction.atoms)
                self.add_interaction(name, atoms, interaction.parameters, interaction.meta)
        for node1, node2 in molecule.edges:
            if correspondence[node1] != correspondence[node2]:
                self.add_edge(correspondence[node1], correspondence[node2])
        return correspondence

    def share_moltype_with(self, other):
        # TODO: Test the node attributes, the molecule attributes, and
        # the interactions.
        return nx.is_isomorphic(self, other)

    def iter_residues(self):
        residue_graph = graph_utils.make_residue_graph(self)
        return (tuple(residue_graph.nodes[res]['graph'].nodes) for res in residue_graph.nodes)

    def edges_between(self, n_bunch1, n_bunch2):
        """
        Returns all edges in this molecule between nodes in `n_bunch1` and
        `n_bunch2`.

        Parameters
        ----------
        n_bunch1: :class:`~collections.abc.Iterable`
            The first bunch of node indices.
        n_bunch2: :class:`~collections.abc.Iterable`
            The second bunch of node indices.

        Returns
        -------
        :class:`list`
            A list of tuples of edges in this molecule. The first element of
            the tuple will be in `n_bunch1`, the second element in `n_bunch2`.
        """
        return [(node1, node2)
                for node1, node2 in itertools.product(n_bunch1, n_bunch2)
                if self.has_edge(node1, node2)]


class Block(Molecule):
    """
    Residue topology template

    Parameters
    ----------
    incoming_graph_data:
        Data to initialize graph. If None (default) an empty graph is created.
    attr:
        Attributes to add to graph as key=value pairs.

    Attributes
    ----------
    name: str or None
        The name of the residue. Set to `None` if undefined.
    atoms: iterator of dict
        The atoms in the residue. Each atom is a dict with *a minima* a key
        'name' for the name of the atom, and a key 'atype' for the atom type.
        An atom can also have a key 'charge', 'charge_group', 'comment', or any
        arbitrary key. 
    interactions: dict
        All the known interactions. Each item of the dictionary is a type of
        interaction, with the key being the name of the kind of interaction
        using Gromacs itp/rtp conventions ('bonds', 'angles', ...) and the
        value being a list of all the interactions of that type in the residue.
        An interaction is a dict with a key 'atoms' under which is stored the
        list of the atoms involved (referred by their name), a key 'parameters'
        under which is stored an arbitrary list of non-atom parameters as
        written in a RTP file, and arbitrary keys to store custom metadata. A
        given interaction can have a comment under the key 'comment'.
    """
    # As the particles are stored as nodes, we want the nodes to stay
    # ordered.
    node_dict_factory = OrderedDict

    def __init__(self, incoming_graph_data=None, **attr):
        super(Block, self).__init__(incoming_graph_data, **attr)
        # Arbitrary attributes can be set during the initialization. We need
        # to set the default of some key attributes, but without overwritting
        # what has been passed in the 'attr' argument.
        defaults = {
            'name': None,
            'interactions': {},
        }
        self._set_defaults(defaults)
        self._apply_to_all_interactions = defaultdict(dict)

    def _set_defaults(self, defaults):
        for attribute, default_value in defaults.items():
            if not hasattr(self, attribute):
                setattr(self, attribute, default_value)

    def __repr__(self):
        name = self.name
        if name is None:
            name = 'Unnamed'
        return '<{} "{}" at 0x{:x}>'.format(self.__class__.__name__,
                                          name, id(self))

    def add_atom(self, atom):
        try:
            name = atom['atomname']
        except KeyError:
            raise ValueError('Atom has no atomname: "{}".'.format(atom))
        self.add_node(name, **atom)

    @property
    def atoms(self):
        for node in self.nodes():
            node_attr = self.node[node]
            # In pre-blocks, some nodes correspond to particles in neighboring
            # residues. These node do not carry particle information and should
            # not appear as particles.
            if node_attr:
                yield node_attr

    def make_edges_from_interaction_type(self, type_):
        """
        Create edges from the interactions of a given type.

        The interactions must be described so that two consecutive atoms in an
        interaction should be linked by an edge. This is the case for bonds,
        angles, proper dihedral angles, and cmap torsions. It is not always
        true for improper torsions.

        Cmap are described as two consecutive proper dihedral angles. The
        atoms for the interaction are the 4 atoms of the first dihedral angle
        followed by the next atom forming the second dihedral angle with the
        3 previous ones. Each pair of consecutive atoms generate an edge.

        .. warning::

            If there is no interaction of the required type, it will be
            silently ignored.

        Parameters
        ----------
        type_: str
            The name of the interaction type the edges should be built from.
        """
        for interaction in self.interactions.get(type_, []):
            if interaction.meta.get('edge', True):
                atoms = interaction.atoms
                self.add_edges_from(zip(atoms[:-1], atoms[1:]))

    def make_edges_from_interactions(self):
        """
        Create edges from the interactions we know how to convert to edges.

        The known interactions are bonds, angles, proper dihedral angles, and
        cmap torsions.
        """
        known_types = ('bonds', 'angles', 'dihedrals', 'cmap', 'constraints')
        for type_ in known_types:
            self.make_edges_from_interaction_type(type_)

    def guess_angles(self):
        for a in self.nodes():
            for b in self.neighbors(a):
                for c in self.neighbors(b):
                    if c == a:
                        continue
                    yield (a, b, c)

    def guess_dihedrals(self, angles=None):
        angles = angles if angles is not None else self.guess_angles()
        for a, b, c in angles:
            for d in self.neighbors(c):
                if d not in (a, b):
                    yield (a, b, c, d)

    def has_dihedral_around(self, center):
        """
        Returns True if the block has a dihedral centered around the given bond.

        Parameters
        ----------
        center: tuple
            The name of the two central atoms of the dihedral angle. The
            method is sensitive to the order.

        Returns
        -------
        bool
        """
        all_centers = [tuple(dih['atoms'][1:-1])
                       for dih in self.interactions.get('dihedrals', [])]
        return tuple(center) in all_centers

    def has_improper_around(self, center):
        """
        Returns True if the block has an improper centered around the given bond.

        Parameters
        ----------
        center: tuple
            The name of the two central atoms of the improper torsion. The
            method is sensitive to the order.

        Returns
        -------
        bool
        """
        all_centers = [tuple(dih.atoms[1:-1])
                       for dih in self.interactions.get('impropers', [])]
        return tuple(center) in all_centers

    def to_molecule(self, atom_offset=0, offset_resid=0, offset_charge_group=0,
                    force_field=None):
        if force_field is None:
            force_field = self.force_field
        name_to_idx = {}
        mol = Molecule(force_field=force_field)
        for idx, node in enumerate(self.nodes, start=atom_offset):
            name_to_idx[node] = idx
            atom = self.nodes[node]
            new_atom = copy.copy(atom)
            new_atom['resid'] = (new_atom.get('resid', 1) + offset_resid)
            new_atom['resname'] = atom.get('resname', self.name)
            new_atom['charge_group'] = (new_atom.get('charge_group', 1)
                                        + offset_charge_group)
            mol.add_node(idx, **new_atom)
        for name, interactions in self.interactions.items():
            for interaction in interactions:
                atoms = tuple(
                    name_to_idx[atom] for atom in interaction.atoms
                )
                mol.add_interaction(
                    name, atoms,
                    interaction.parameters
                )
        for edge in self.edges:
            mol.add_edge(*(name_to_idx[node] for node in edge))

        try:
            mol.nrexcl = self.nrexcl
        except AttributeError:
            pass

        return mol


class Link(Block):
    """
    Template link between two residues.

    Parameters
    ----------
    incoming_graph_data:
        Data to initialize graph. If None (default) an empty graph is created.
    attr:
        Attributes to add to graph as key=value pairs.
    """
    node_dict_factory = OrderedDict

    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)
        # Arbitrary attributes can be set during the initialization. We need
        # to set the default of some key attributes, but without overwritting
        # what has been passed in the 'attr' argument.
        defaults = {
            'non_edges': [],
            'removed_interactions': {},
            'molecule_meta': {},
            'patterns': [],
            'features': [],
        }
        self._set_defaults(defaults)
        self._apply_to_all_nodes = {}


def attributes_match(attributes, template_attributes, ignore_keys=()):
    """
    Compare a dict of attributes from a molecule with one from a link.

    Returns ``True`` if the attributes from the link match the ones from the
    molecule; returns ``False`` otherwise. The attributes from a link match
    with those of a molecule is all the individual attribute from the link
    match the corresponding ones in the molecule. In the simplest case, these
    attribute match if their values are equal. If the value of the link
    attribute is an instance of :class:`LinkPredicate`, then the attributes
    match if the ``match`` method of the predicate returns ``True``.

    Parameters
    ----------
    attributes: dict
        Attributes from the molecule.
    template_attributes: dict
        Attributes from the link.
    ignore_keys: list
        List of keys to ignore from 'template_attributes'.

    Returns
    -------
    bool
    """
    for attr, value in template_attributes.items():
        if attr in ignore_keys:
            continue
        if isinstance(value, LinkPredicate):
            if not value.match(attributes, attr):
                return False
        elif attributes.get(attr) != value:
            return False
    return True


def interaction_match(molecule, interaction, template_interaction):
    """
    Compare an interaction with a template interaction or interaction to delete.

    An instance of :class:`Interaction` matches a template instance of the same
    class or of :class:`DeleteInteraction` if, at the  minimum, it involves the
    same atoms in the same order. If the template defines parameters, then they
    have to match as well. In the case of of a :class:`DeleteInteraction`,
    atoms may have attributes as well, then they have to match with the
    attributes of the corresponding atoms in the molecule.

    Parameters
    ----------
    molecule: nx.Graph
        The molecule that contains the interaction.
    interaction: Interaction
        The interaction in the molecule.
    template_interaction: Interaction or DeleteInteraction
        The template to match with the interaction.

    Returns
    -------
    bool

    See Also
    --------
    attributes_match
    """
    atoms_match = tuple(template_interaction.atoms) == tuple(interaction.atoms)
    parameters_match = (
        not template_interaction.parameters
        or tuple(template_interaction.parameters) == tuple(interaction.parameters)
    )
    if atoms_match and parameters_match:
        try:
            atom_attrs = template_interaction.atom_attrs
        except AttributeError:
            atom_attrs = [{}, ] * len(template_interaction.atoms)
        nodes = [molecule.nodes[atom] for atom in interaction.atoms]
        for atom, template_atom in zip(nodes, atom_attrs):
            if not attributes_match(atom, template_atom):
                return False
        return attributes_match(interaction.meta, template_interaction.meta)
    return False


if __name__ == '__main__':
    mol = Molecule()
    mol.add_edge(0, 1)
    mol.add_edge(1, 2)
    nx.subgraph(mol, (0, 1))

    mol.add_interaction('bond', (0, 1), tuple((1, 2)))
    mol.add_interaction('bond', (1, 2), tuple((10, 20)))
    mol.add_angle((0, 1, 2), tuple([10, 2, 3]))

    print(mol.interactions)
    print(mol.get_interaction('bond'))
    print(mol.get_bonds())
    print(mol.get_angles())

    mol.remove_interaction('bond', (0, 3))
    print(mol.get_bonds())