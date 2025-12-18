import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any

class ResultMapper:
    """
    Orchestrates the transformation of raw algorithmic results (Numpy Arrays) 
    into business-relevant, readable data structures (Pandas DataFrame)
    """

    def __init__(
        self, 
        variable_names: List[str], 
        objective_names: List[str], 
        discrete_maps: Optional[Dict[str, Dict[int, Any]]] = None
    ):
        """
        Initializes the ResultMapper instance.
        """
        self.variable_names = variable_names
        self.objective_names = objective_names
        self.discrete_maps = discrete_maps if discrete_maps else {}

    def map_to_dataframe(self, res) -> pd.DataFrame:
        """
        Main method to convert raw results into a Pandas DataFrame.
        """
        if res is None or res.X is None:
            print("warning: No results to map; returning empty DataFrame.")
            return pd.DataFrame()

        # convert raw decision variables (res.X)into a labelled DataFrame using the defined variable names -> creates left part of final DataFrame
        df_design = pd.DataFrame(res.X, columns=self.variable_names)
        
        # Apply mapping to convert numerical indices into readable labels for discrete variables -> transforms numerical codes into readable names
        df_design = self._apply_discrete_mappings(df_design)

        # Create a separate DataFrame for the objectives/results (res.F) -> creates right part of final DataFrame
        df_objectives = pd.DataFrame(res.F, columns=self.objective_names)

        # Merge inputs (left) and outputs (right) side-by-side (axis=1) into one complete table
        final_df = pd.concat([df_design, df_objectives], axis=1)

       # Optionally, check feasibility if constraint results (res.G) are available
        if hasattr(res, 'G') and res.G is not None:
            # Feasibility: All constraints must be <= 0 to be feasible
            is_feasible = np.all(res.G <= 0, axis=1)
            final_df['is_feasible'] = is_feasible

        return final_df

    def _apply_discrete_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Internal method to map discrete variable indices to their corresponding labels.
        """
        for col_name, mapping_dict in self.discrete_maps.items():
            if col_name in df.columns:
                try:
                    # Round values to nearest integer and map using the provided dictionary
                    df[col_name] = df[col_name].round().astype(int).map(mapping_dict)
                    
                    # Fill unmapped values with a default label
                    df[col_name] = df[col_name].fillna("Unknown")
                except Exception as e:
                    print(f"Error mapping column '{col_name}': {e}")
        
        return df