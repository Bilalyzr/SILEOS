/* ============================================================
   CBSE Curriculum Map — Classes 6–12, every chapter.
   c: complexity 1=Foundation, 2=Core, 3=Advanced
   lab: path to a built simulation (null = in the roadmap queue)
   ============================================================ */
var CURRICULUM = [
  {
    cls: 6, theme: 'Foundations — observing the world',
    subjects: [
      { name: 'Science', chapters: [
        { n: 'Components of Food', c: 1, lab: null },
        { n: 'Sorting Materials into Groups', c: 1, lab: null },
        { n: 'Separation of Substances', c: 1, lab: null },
        { n: 'Getting to Know Plants', c: 1, lab: 'labs/biology/photosynthesis-lab.html' },
        { n: 'Body Movements', c: 1, lab: null },
        { n: 'The Living Organisms and Their Surroundings', c: 1, lab: 'labs/science/predator-prey.html' },
        { n: 'Motion and Measurement of Distances', c: 1, lab: 'labs/science/motion-graphs.html' },
        { n: 'Light, Shadows and Reflections', c: 1, lab: 'labs/science/light-optics.html' },
        { n: 'Electricity and Circuits', c: 2, lab: 'labs/science/electric-circuits.html' },
        { n: 'Fun with Magnets', c: 1, lab: 'labs/science/magnet-lab.html' },
        { n: 'Water & Air Around Us', c: 1, lab: null },
        { n: 'Beyond Earth (sky & solar system)', c: 2, lab: 'labs/science/solar-system-3d.html', x: '3D lab' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Knowing Our Numbers', c: 1, lab: null },
        { n: 'Whole Numbers', c: 1, lab: null },
        { n: 'Playing with Numbers', c: 1, lab: null },
        { n: 'Basic Geometrical Ideas', c: 1, lab: null },
        { n: 'Understanding Elementary Shapes', c: 1, lab: null },
        { n: 'Integers', c: 2, lab: null },
        { n: 'Fractions', c: 2, lab: 'labs/math/fractions-explorer.html' },
        { n: 'Decimals', c: 2, lab: 'labs/math/fractions-explorer.html' },
        { n: 'Data Handling', c: 1, lab: null },
        { n: 'Mensuration', c: 2, lab: 'labs/math/solids-3d.html', x: '3D lab' },
        { n: 'Algebra', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Ratio and Proportion', c: 2, lab: null },
        { n: 'Symmetry', c: 1, lab: null }
      ]}
    ]
  },
  {
    cls: 7, theme: 'Building blocks — how things work',
    subjects: [
      { name: 'Science', chapters: [
        { n: 'Nutrition in Plants', c: 1, lab: 'labs/biology/photosynthesis-lab.html' },
        { n: 'Nutrition in Animals', c: 1, lab: null },
        { n: 'Heat', c: 2, lab: 'labs/science/heat-transfer-lab.html' },
        { n: 'Acids, Bases and Salts', c: 2, lab: 'labs/science/acids-bases-ph.html' },
        { n: 'Physical and Chemical Changes', c: 2, lab: null },
        { n: 'Respiration in Organisms', c: 1, lab: null },
        { n: 'Transportation in Animals and Plants', c: 2, lab: null },
        { n: 'Reproduction in Plants', c: 1, lab: null },
        { n: 'Motion and Time', c: 2, lab: 'labs/science/motion-graphs.html' },
        { n: 'Electric Current and its Effects', c: 2, lab: 'labs/science/electric-circuits.html' },
        { n: 'Light', c: 2, lab: 'labs/science/light-optics.html' },
        { n: 'Forests: Our Lifeline', c: 1, lab: 'labs/science/predator-prey.html' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Integers', c: 2, lab: null },
        { n: 'Fractions and Decimals', c: 2, lab: 'labs/math/fractions-explorer.html' },
        { n: 'Data Handling', c: 1, lab: 'labs/math/probability-lab.html' },
        { n: 'Simple Equations', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Lines and Angles', c: 2, lab: null },
        { n: 'The Triangle and its Properties', c: 2, lab: 'labs/math/pythagoras-explorer.html' },
        { n: 'Comparing Quantities', c: 2, lab: null },
        { n: 'Rational Numbers', c: 2, lab: null },
        { n: 'Perimeter and Area', c: 2, lab: null },
        { n: 'Algebraic Expressions', c: 2, lab: null },
        { n: 'Exponents and Powers', c: 2, lab: null },
        { n: 'Symmetry', c: 1, lab: null },
        { n: 'Visualising Solid Shapes', c: 2, lab: 'labs/math/solids-3d.html', x: '3D lab' }
      ]}
    ]
  },
  {
    cls: 8, theme: 'Connecting concepts — systems interact',
    subjects: [
      { name: 'Science', chapters: [
        { n: 'Crop Production and Management', c: 1, lab: null },
        { n: 'Microorganisms: Friend and Foe', c: 2, lab: null },
        { n: 'Coal and Petroleum', c: 2, lab: null },
        { n: 'Combustion and Flame', c: 2, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Conservation of Plants and Animals', c: 1, lab: null },
        { n: 'Reproduction in Animals', c: 1, lab: null },
        { n: 'Reaching the Age of Adolescence', c: 1, lab: null },
        { n: 'Force and Pressure', c: 2, lab: 'labs/science/force-pressure-friction.html' },
        { n: 'Friction', c: 2, lab: 'labs/science/force-pressure-friction.html' },
        { n: 'Sound', c: 2, lab: 'labs/physics/wave-motion.html' },
        { n: 'Chemical Effects of Electric Current', c: 3, lab: 'labs/science/electric-circuits.html' },
        { n: 'Some Natural Phenomena (lightning, earthquakes)', c: 3, lab: null },
        { n: 'Light', c: 2, lab: 'labs/science/light-optics.html' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Rational Numbers', c: 2, lab: null },
        { n: 'Linear Equations in One Variable', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Understanding Quadrilaterals', c: 2, lab: null },
        { n: 'Data Handling', c: 2, lab: 'labs/math/probability-lab.html' },
        { n: 'Squares and Square Roots', c: 2, lab: 'labs/math/pythagoras-explorer.html' },
        { n: 'Cubes and Cube Roots', c: 2, lab: null },
        { n: 'Comparing Quantities', c: 2, lab: null },
        { n: 'Algebraic Expressions and Identities', c: 3, lab: null },
        { n: 'Mensuration', c: 2, lab: null },
        { n: 'Exponents and Powers', c: 2, lab: null },
        { n: 'Direct and Inverse Proportions', c: 2, lab: null },
        { n: 'Factorisation', c: 3, lab: null },
        { n: 'Introduction to Graphs', c: 2, lab: 'labs/math/line-explorer.html' }
      ]}
    ]
  },
  {
    cls: 9, theme: 'The bridge year — science becomes quantitative',
    subjects: [
      { name: 'Science', chapters: [
        { n: 'Matter in Our Surroundings', c: 1, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Is Matter Around Us Pure?', c: 2, lab: null },
        { n: 'Atoms and Molecules', c: 2, lab: 'labs/chemistry/molecule-viewer-3d.html', x: '3D lab' },
        { n: 'Structure of the Atom', c: 3, lab: 'labs/science/atom-builder-3d.html', x: '3D lab' },
        { n: 'The Fundamental Unit of Life', c: 2, lab: 'labs/science/plant-animal-cell.html' },
        { n: 'Tissues', c: 2, lab: 'labs/science/plant-animal-cell.html' },
        { n: 'Motion', c: 2, lab: 'labs/science/motion-graphs.html' },
        { n: 'Force and Laws of Motion', c: 3, lab: null },
        { n: 'Gravitation', c: 3, lab: 'labs/physics/projectile-motion.html' },
        { n: 'Work and Energy', c: 3, lab: 'labs/physics/simple-pendulum.html' },
        { n: 'Sound', c: 3, lab: 'labs/physics/wave-motion.html' },
        { n: 'Improvement in Food Resources', c: 1, lab: null }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Number Systems', c: 2, lab: null },
        { n: 'Polynomials', c: 2, lab: 'labs/math/quadratic-explorer.html' },
        { n: 'Coordinate Geometry', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Linear Equations in Two Variables', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Introduction to Euclid\u2019s Geometry', c: 1, lab: null },
        { n: 'Lines and Angles', c: 2, lab: null },
        { n: 'Triangles', c: 3, lab: 'labs/math/pythagoras-explorer.html' },
        { n: 'Quadrilaterals', c: 2, lab: null },
        { n: 'Circles', c: 3, lab: null },
        { n: 'Heron\u2019s Formula', c: 2, lab: null },
        { n: 'Surface Areas and Volumes', c: 2, lab: null },
        { n: 'Statistics', c: 2, lab: 'labs/math/statistics-lab.html' }
      ]}
    ]
  },
  {
    cls: 10, theme: 'Board year — synthesize and apply',
    subjects: [
      { name: 'Science', chapters: [
        { n: 'Chemical Reactions and Equations', c: 2, lab: 'labs/science/balance-equations.html' },
        { n: 'Acids, Bases and Salts', c: 2, lab: 'labs/science/acids-bases-ph.html' },
        { n: 'Metals and Non-metals', c: 2, lab: 'labs/science/reactivity-series.html' },
        { n: 'Carbon and its Compounds', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html', x: '3D lab' },
        { n: 'Life Processes', c: 3, lab: 'labs/biology/photosynthesis-lab.html' },
        { n: 'Control and Coordination', c: 3, lab: null },
        { n: 'How do Organisms Reproduce?', c: 2, lab: null },
        { n: 'Heredity', c: 3, lab: 'labs/biology/genetics-punnett.html' },
        { n: 'Light — Reflection and Refraction', c: 3, lab: 'labs/science/light-optics.html' },
        { n: 'The Human Eye and the Colourful World', c: 3, lab: 'labs/science/human-eye-lab.html' },
        { n: 'Electricity', c: 3, lab: 'labs/science/electric-circuits.html' },
        { n: 'Magnetic Effects of Electric Current', c: 3, lab: 'labs/science/magnetism-current.html' },
        { n: 'Our Environment', c: 1, lab: 'labs/science/predator-prey.html' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Real Numbers', c: 2, lab: null },
        { n: 'Polynomials', c: 2, lab: 'labs/math/quadratic-explorer.html' },
        { n: 'Pair of Linear Equations in Two Variables', c: 3, lab: 'labs/math/line-explorer.html' },
        { n: 'Quadratic Equations', c: 3, lab: 'labs/math/quadratic-explorer.html' },
        { n: 'Arithmetic Progressions', c: 3, lab: null },
        { n: 'Triangles', c: 3, lab: 'labs/math/pythagoras-explorer.html' },
        { n: 'Coordinate Geometry', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Introduction to Trigonometry', c: 3, lab: 'labs/math/trigonometry-explorer.html' },
        { n: 'Some Applications of Trigonometry', c: 3, lab: null },
        { n: 'Circles', c: 3, lab: null },
        { n: 'Areas Related to Circles', c: 3, lab: null },
        { n: 'Surface Areas and Volumes', c: 2, lab: null },
        { n: 'Statistics', c: 2, lab: 'labs/math/probability-lab.html' },
        { n: 'Probability', c: 2, lab: 'labs/math/probability-lab.html' }
      ]}
    ]
  },
  {
    cls: 11, theme: 'Specialization begins — choose your stream',
    subjects: [
      { name: 'Physics', chapters: [
        { n: 'Units and Measurement', c: 1, lab: null },
        { n: 'Motion in a Straight Line', c: 2, lab: 'labs/science/motion-graphs.html' },
        { n: 'Motion in a Plane', c: 3, lab: 'labs/physics/projectile-motion.html' },
        { n: 'Laws of Motion', c: 3, lab: null },
        { n: 'Work, Energy and Power', c: 3, lab: 'labs/physics/simple-pendulum.html' },
        { n: 'System of Particles and Rotational Motion', c: 3, lab: null },
        { n: 'Gravitation', c: 3, lab: 'labs/physics/projectile-motion.html' },
        { n: 'Mechanical Properties of Solids', c: 2, lab: null },
        { n: 'Mechanical Properties of Fluids', c: 3, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Thermal Properties of Matter', c: 2, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Thermodynamics', c: 3, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Kinetic Theory', c: 3, lab: 'labs/chemistry/ideal-gas-lab.html' },
        { n: 'Oscillations', c: 3, lab: 'labs/physics/simple-pendulum.html' },
        { n: 'Waves', c: 3, lab: 'labs/physics/wave-motion.html' }
      ]},
      { name: 'Chemistry', chapters: [
        { n: 'Some Basic Concepts of Chemistry', c: 2, lab: 'labs/chemistry/titration-lab.html' },
        { n: 'Structure of Atom', c: 3, lab: 'labs/science/atom-builder-3d.html', x: '3D lab' },
        { n: 'Classification of Elements and Periodicity', c: 3, lab: null },
        { n: 'Chemical Bonding and Molecular Structure', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html', x: '3D lab' },
        { n: 'Thermodynamics', c: 3, lab: null },
        { n: 'Equilibrium', c: 3, lab: 'labs/chemistry/titration-lab.html' },
        { n: 'Redox Reactions', c: 3, lab: null },
        { n: 'Organic Chemistry: Basic Principles', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' },
        { n: 'Hydrocarbons', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Sets', c: 1, lab: null },
        { n: 'Relations and Functions', c: 2, lab: null },
        { n: 'Trigonometric Functions', c: 3, lab: 'labs/math/unit-circle-lab.html' },
        { n: 'Complex Numbers and Quadratic Equations', c: 3, lab: 'labs/math/quadratic-explorer.html' },
        { n: 'Linear Inequalities', c: 2, lab: null },
        { n: 'Permutations and Combinations', c: 3, lab: 'labs/math/probability-lab.html' },
        { n: 'Binomial Theorem', c: 3, lab: null },
        { n: 'Sequences and Series', c: 3, lab: null },
        { n: 'Straight Lines', c: 2, lab: 'labs/math/line-explorer.html' },
        { n: 'Conic Sections', c: 3, lab: 'labs/math/conic-sections-3d.html', x: '3D lab' },
        { n: 'Introduction to Three-Dimensional Geometry', c: 2, lab: null, x: '3D-ready' },
        { n: 'Limits and Derivatives', c: 3, lab: null },
        { n: 'Statistics', c: 2, lab: 'labs/math/probability-lab.html' },
        { n: 'Probability', c: 3, lab: 'labs/math/probability-lab.html' }
      ]},
      { name: 'Biology', chapters: [
        { n: 'The Living World', c: 1, lab: null },
        { n: 'Biological Classification', c: 2, lab: null },
        { n: 'Plant Kingdom', c: 2, lab: null },
        { n: 'Animal Kingdom', c: 2, lab: null },
        { n: 'Morphology of Flowering Plants', c: 2, lab: null },
        { n: 'Anatomy of Flowering Plants', c: 2, lab: 'labs/science/plant-animal-cell.html' },
        { n: 'Structural Organisation in Animals', c: 2, lab: null },
        { n: 'Cell: The Unit of Life', c: 2, lab: 'labs/science/plant-animal-cell.html' },
        { n: 'Biomolecules', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' },
        { n: 'Cell Cycle and Cell Division', c: 3, lab: null },
        { n: 'Photosynthesis in Higher Plants', c: 3, lab: 'labs/biology/photosynthesis-lab.html' },
        { n: 'Respiration in Plants', c: 3, lab: null },
        { n: 'Plant Growth and Development', c: 3, lab: null },
        { n: 'Breathing and Exchange of Gases', c: 2, lab: null },
        { n: 'Body Fluids and Circulation', c: 3, lab: null },
        { n: 'Excretory Products and Elimination', c: 3, lab: null },
        { n: 'Locomotion and Movement', c: 2, lab: null },
        { n: 'Neural Control and Coordination', c: 3, lab: null },
        { n: 'Chemical Coordination and Integration', c: 3, lab: null }
      ]}
    ]
  },
  {
    cls: 12, theme: 'Mastery — engineering, medicine & beyond',
    subjects: [
      { name: 'Physics', chapters: [
        { n: 'Electric Charges and Fields', c: 3, lab: null },
        { n: 'Electrostatic Potential and Capacitance', c: 3, lab: null },
        { n: 'Current Electricity', c: 3, lab: 'labs/science/electric-circuits.html' },
        { n: 'Moving Charges and Magnetism', c: 3, lab: null },
        { n: 'Magnetism and Matter', c: 2, lab: null },
        { n: 'Electromagnetic Induction', c: 3, lab: 'labs/physics/faraday-lab.html' },
        { n: 'Alternating Current', c: 3, lab: null },
        { n: 'Electromagnetic Waves', c: 2, lab: 'labs/physics/wave-motion.html' },
        { n: 'Ray Optics and Optical Instruments', c: 3, lab: 'labs/science/light-optics.html' },
        { n: 'Wave Optics', c: 3, lab: 'labs/physics/wave-motion.html' },
        { n: 'Dual Nature of Radiation and Matter', c: 3, lab: null },
        { n: 'Atoms', c: 3, lab: 'labs/science/atom-builder-3d.html', x: '3D lab' },
        { n: 'Nuclei', c: 3, lab: 'labs/science/atom-builder-3d.html' },
        { n: 'Semiconductor Electronics', c: 3, lab: 'labs/science/electric-circuits.html' }
      ]},
      { name: 'Chemistry', chapters: [
        { n: 'Solutions', c: 3, lab: 'labs/chemistry/titration-lab.html' },
        { n: 'Electrochemistry', c: 3, lab: null },
        { n: 'Chemical Kinetics', c: 3, lab: 'labs/chemistry/kinetics-lab.html' },
        { n: 'The d- and f-Block Elements', c: 3, lab: null },
        { n: 'Coordination Compounds', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' },
        { n: 'Haloalkanes and Haloarenes', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' },
        { n: 'Alcohols, Phenols and Ethers', c: 3, lab: 'labs/chemistry/molecule-viewer-3d.html' },
        { n: 'Aldehydes, Ketones and Carboxylic Acids', c: 3, lab: null },
        { n: 'Amines', c: 3, lab: null },
        { n: 'Biomolecules', c: 2, lab: 'labs/chemistry/molecule-viewer-3d.html' }
      ]},
      { name: 'Mathematics', chapters: [
        { n: 'Relations and Functions', c: 2, lab: null },
        { n: 'Inverse Trigonometric Functions', c: 3, lab: null },
        { n: 'Matrices', c: 2, lab: null },
        { n: 'Determinants', c: 3, lab: null },
        { n: 'Continuity and Differentiability', c: 3, lab: null },
        { n: 'Application of Derivatives', c: 3, lab: null },
        { n: 'Integrals', c: 3, lab: null },
        { n: 'Application of Integrals', c: 3, lab: null },
        { n: 'Differential Equations', c: 3, lab: null },
        { n: 'Vector Algebra', c: 2, lab: null },
        { n: 'Three-Dimensional Geometry', c: 3, lab: null, x: '3D-ready' },
        { n: 'Linear Programming', c: 2, lab: null },
        { n: 'Probability', c: 3, lab: 'labs/math/probability-lab.html' }
      ]},
      { name: 'Biology', chapters: [
        { n: 'Sexual Reproduction in Flowering Plants', c: 3, lab: null },
        { n: 'Human Reproduction', c: 3, lab: null },
        { n: 'Reproductive Health', c: 2, lab: null },
        { n: 'Principles of Inheritance and Variation', c: 3, lab: 'labs/biology/genetics-punnett.html' },
        { n: 'Molecular Basis of Inheritance', c: 3, lab: 'labs/biology/dna-helix-3d.html', x: '3D lab' },
        { n: 'Evolution', c: 3, lab: 'labs/science/predator-prey.html' },
        { n: 'Human Health and Disease', c: 2, lab: null },
        { n: 'Microbes in Human Welfare', c: 2, lab: null },
        { n: 'Biotechnology: Principles and Processes', c: 3, lab: 'labs/biology/dna-helix-3d.html' },
        { n: 'Biotechnology and its Applications', c: 3, lab: null },
        { n: 'Organisms and Populations', c: 2, lab: 'labs/science/predator-prey.html' },
        { n: 'Ecosystem', c: 2, lab: 'labs/science/predator-prey.html' },
        { n: 'Biodiversity and Conservation', c: 2, lab: null }
      ]}
    ]
  }
];

/* Complexity legend + standard resource pack every chapter ships with */
var COMPLEXITY = {
  1: { label: 'Foundation', color: '#16a34a', hint: 'Everyday intuition — observe, sort, name.' },
  2: { label: 'Core', color: '#d97706', hint: 'Board-exam central — formulas, laws, practice.' },
  3: { label: 'Advanced', color: '#f43f5e', hint: 'Analytical depth — derivations, interlinked ideas.' }
};
var RESOURCE_PACK = ['Concept notes', 'Solved examples', 'Practice quiz', 'Board-pattern questions'];
