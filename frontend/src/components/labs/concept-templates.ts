import type { ConceptConfig, LabEngine } from "@/api/lab-studio";

export const engines: {
  id: LabEngine;
  label: string;
  objective: string;
  prediction: string;
  steps: string[];
}[] = [
  {id:'supplied',label:'Your supplied simulation',objective:'Investigate the selected simulation and explain your observations.',prediction:'What do you predict will happen when you change one variable?',steps:['Explore the simulation controls.','Change one variable and record your observations.','Explain whether the result supports your prediction.']},
  {
    id: "linear",
    label: "Linear relationships",
    objective: "Explain how slope and intercept change a straight-line graph.",
    prediction:
      "What happens to y when the slope doubles while the intercept stays fixed?",
    steps: [
      "Choose a slope and intercept. Capture the first trial.",
      "Double the slope. Compare y at x = 2.",
      "Keep the slope fixed and change the intercept. Explain what moved.",
    ],
  },
  {
    id: "projectile",
    label: "Projectile motion",
    objective:
      "Investigate launch angle, speed and gravity in an ideal projectile model.",
    prediction: "Which launch angle gives the greatest range on level ground?",
    steps: [
      "Compare 30°, 45° and 60° at the same speed.",
      "Change gravity while keeping angle and speed fixed.",
      "Explain the assumptions that make your comparison valid.",
    ],
  },
  {
    id: "pendulum",
    label: "Pendulum oscillations",
    objective:
      "Relate length and gravity to the period of a small-angle pendulum.",
    prediction: "Will doubling the length double the period?",
    steps: [
      "Capture a trial at a length of 1 metre.",
      "Compare periods at 2 and 4 metres.",
      "Use the square-root relationship to explain the result.",
    ],
  },
  {
    id: "circuit",
    label: "Ohm’s law",
    objective: "Measure current and power as voltage and resistance change.",
    prediction: "What happens to current when resistance doubles?",
    steps: [
      "Set voltage to 12 V and resistance to 10 Ω.",
      "Double resistance while keeping voltage fixed.",
      "Explain why this model describes an ideal ohmic resistor.",
    ],
  },
  {
    id: "gas",
    label: "Ideal gas relationships",
    objective:
      "Explore pressure, temperature, volume and amount in the ideal gas model.",
    prediction: "What happens to pressure when volume is halved?",
    steps: [
      "Capture a trial at 300 K, 10 L and 1 mol.",
      "Halve the volume while holding other variables fixed.",
      "Change temperature and compare the pressure ratio.",
    ],
  },
  {
    id: "wave",
    label: "Wave relationships",
    objective: "Connect frequency, wave speed and wavelength.",
    prediction:
      "How does wavelength change when frequency doubles at constant speed?",
    steps: [
      "Measure wavelength at 1 Hz and 4 m/s.",
      "Double frequency, then separately double wave speed.",
      "Explain which variable changes the height of the graph.",
    ],
  },
  {
    id: "classification",
    label: "Concept classification",
    objective: "Classify examples by a clear rule and explain each decision.",
    prediction: "Which features distinguish the two groups?",
    steps: [
      "Read each example and predict its group.",
      "Assign every example, then check your reasoning.",
      "Explain one difficult decision and add a counterexample.",
    ],
  },
];

export function templateConfig(engine: LabEngine): ConceptConfig {
  const entry = engines.find((e) => e.id === engine)!;
  return {
    engine,
    ...(engine === "supplied" ? {source_slug:"cbse-fractions-explorer"} : {}),
    objective: entry.objective,
    prediction: entry.prediction,
    investigation: [...entry.steps],
    explanation: "",
    chapter_ids: [],
    cards:
      engine === "classification"
        ? [
            {
              label: "Copper wire",
              group: "Conductor",
              explanation: "Copper contains mobile charge carriers.",
            },
            {
              label: "Aluminium foil",
              group: "Conductor",
              explanation: "Aluminium is a conducting metal.",
            },
            {
              label: "Dry rubber",
              group: "Insulator",
              explanation: "Charge carriers are not free to move easily.",
            },
          ]
        : [],
  };
}
