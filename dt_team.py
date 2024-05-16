import json

design_thinking_team = {
    'Designer': {"name": "Designer", "description": "Creates wireframes, prototypes, and high-fidelity designs. Designs intuitive and engaging user interfaces across various platforms. Collaborates with developers to ensure design feasibility and consistency."},
    'Business Analyst': {"name": "Business Analyst", "description": "Represents the business perspective and stakeholder needs. Ensures the design aligns with business goals and requirements. Helps define success metrics and KPIs for the project."},
    'Developer': {"name": "Developer", "description": "Provides technical expertise and feasibility input during the design process. Collaborates with designers to understand design intent and constraints. Develops and implements the designed solution."},
    'Product Manager': {"name": "Product Manager", "description": "Defines the product vision, strategy, and roadmap. Prioritizes features and user stories based on business value and user needs. Ensures the design aligns with the overall product strategy."},
    'Sponsor/Stakeholder': {"name": "Sponsor/Stakeholder", "description": "Provides executive support and resources for the project. Offers insights into business goals, constraints, and opportunities. Champions the design thinking approach within the organization."},

    
}

with open('design_thinking_team.json', 'w') as f:
    json.dump(design_thinking_team, f)