import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="KEAM Engineering Rank Generator",
    layout="wide"
)

st.title("KEAM Engineering Rank List Generator")

# -------------------------------------------------
# Upload Files
# -------------------------------------------------

mark_file = st.file_uploader(
    "markinputs.xlsx",
    type=["xlsx"]
)

max_file = st.file_uploader(
    "maximummarks.xlsx",
    type=["xlsx"]
)

entrance_file = st.file_uploader(
    "tblEnggNormCandSubMarks.xlsx",
    type=["xlsx"]
)

candidate_file = st.file_uploader(
    "candidates.xlsx",
    type=["xlsx"]
)
subject_file = st.file_uploader(
    "tblCandSubMarks.xlsx",
    type=["xlsx"]
)
# -------------------------------------------------
# Generate Ranklist
# -------------------------------------------------

if all([
    mark_file,
    max_file,
    entrance_file,
    candidate_file,
    subject_file
]):

    marks = pd.read_excel(mark_file)
    maxmarks = pd.read_excel(max_file)
    entrance = pd.read_excel(entrance_file)
    candidates = pd.read_excel(candidate_file)
    submarks = pd.read_excel(subject_file)
    # Remove duplicate application records
    marks = marks.drop_duplicates(
        subset=["ApplNo"],
        keep="first"
    )
    
    # Remove duplicate candidate records
    candidates = candidates.drop_duplicates(
        subset=["ApplNo"],
        keep="first"
    )
    
    # Remove duplicate entrance records
    entrance = entrance.drop_duplicates(
        subset=["RollNo"],
        keep="first"
    )

    st.success("All files loaded successfully")
    # -----------------------------------
# Subject Wise Entrance Details
# -----------------------------------

    physics = (
        submarks[submarks["intSubjectID"] == 1]
        [["intRollNo","decSubTotCorr","intCount"]]
        .rename(
            columns={
                "intRollNo":"RollNo",
                "decSubTotCorr":"PhysicsEntranceRaw",
                "intCount":"PhysicsCorrect"
            }
        )
        .groupby("RollNo", as_index=False)
        .agg({
            "PhysicsEntranceRaw":"max",
            "PhysicsCorrect":"max"
        })
    )
    
    maths = (
        submarks[submarks["intSubjectID"] == 3]
        [["intRollNo","decSubTotCorr","intCount"]]
        .rename(
            columns={
                "intRollNo":"RollNo",
                "decSubTotCorr":"MathsEntranceRaw",
                "intCount":"MathsCorrect"
            }
        )
        .groupby("RollNo", as_index=False)
        .agg({
            "MathsEntranceRaw":"max",
            "MathsCorrect":"max"
        })
    )
    

    # -------------------------------------------------
    # Merge Board Maximums
    # -------------------------------------------------

    df = pd.merge(
        marks,
        maxmarks,
        left_on=["BOARD", "YEARPASS"],
        right_on=["BOARD", "YEAR"],
        how="left"
    )
    missing_max = df[
        df["MATMAXMARK"].isna()
    ]
    
    if len(missing_max) > 0:
    
        st.error(
            "Missing board/year maximum marks"
        )
    
        st.dataframe(
            missing_max[
                ["ApplNo","BOARD","YEARPASS"]
            ]
        )
    
        st.stop()
    

    # -------------------------------------------------
    # KEAM Normalization Formula
    #
    # YB = (100 * XjB) / HjB
    # -------------------------------------------------

    df["NormMath"] = (
        100 *
        df["MATHS_MARK"]
    ) / df["MATMAXMARK"]

    df["NormPhy"] = (
        100 *
        df["PHY_MARK"]
    ) / df["PHYMAXMARK"]

    df["NormChem"] = (
        100 *
        df["CHE_MARK"]
    ) / df["CHEMAXMARK"]

    # -------------------------------------------------
    # Weightage 5:3:2
    #
    # Maths = 150
    # Physics = 90
    # Chemistry = 60
    # Total = 300
    # -------------------------------------------------

    df["MathWeighted"] = (
        df["NormMath"] * 150 / 100
    )

    df["PhyWeighted"] = (
        df["NormPhy"] * 90 / 100
    )

    df["ChemWeighted"] = (
        df["NormChem"] * 60 / 100
    )

    df["PlusTwoScore"] = (
        df["MathWeighted"] +
        df["PhyWeighted"] +
        df["ChemWeighted"]
    )

    # -------------------------------------------------
    # Candidate Details
    # -------------------------------------------------

   # Candidate Details

    df = pd.merge(
        df,
        candidates[
            ["ApplNo","RollNo","Name","DOB"]
        ],
        on="ApplNo",
        how="left"
    )
    missing_roll = df[df["RollNo"].isna()]

    if len(missing_roll) > 0:
    
        st.error(
            f"{len(missing_roll)} candidates have no Roll Number"
        )
    
        st.dataframe(
            missing_roll[
                ["ApplNo","Name"]
            ]
        )
    
        st.stop()
    # Maths Tie Break
    
    df = pd.merge(
        df,
        maths,
        on="RollNo",
        how="left"
    )
    
    # Physics Tie Break
    
    df = pd.merge(
        df,
        physics,
        on="RollNo",
        how="left"
    )
    
    # Entrance Score
    
    df = pd.merge(
        df,
        entrance,
        on="RollNo",
        how="left"
    )
    missing_norm = df[
        df["Norm_Score"].isna()
    ]
    
    if len(missing_norm) > 0:
    
        st.warning(
            f"{len(missing_norm)} candidates missing entrance score"
        )
    df["Norm_Score"] = pd.to_numeric(
        df["Norm_Score"],
        errors="coerce"
    ).fillna(0)

    # -------------------------------------------------
    # Final Index Mark
    #
    # PlusTwo (300)
    # +
    # KEAM Normalized Score (300)
    #
    # Total = 600
    # -------------------------------------------------

    df["IndexMark"] = (
        df["PlusTwoScore"] +
        df["Norm_Score"]
    )

    # -------------------------------------------------
    # Rounding
    # -------------------------------------------------

    df["NormMath"] = df["NormMath"].round(4)
    df["NormPhy"] = df["NormPhy"].round(4)
    df["NormChem"] = df["NormChem"].round(4)

    df["PlusTwoScore"] = (
        df["PlusTwoScore"]
        .round(4)
    )

    df["IndexMark"] = (
        df["IndexMark"]
        .round(4)
    )

    # -------------------------------------------------
    # DOB
    # Older candidate gets preference
    # -------------------------------------------------

    df["DOB"] = pd.to_datetime(
        df["DOB"],
        errors="coerce"
    )

    # -------------------------------------------------
    # Official KEAM Tie Resolution
    # -------------------------------------------------

    required_columns = [
        "MathsEntranceRaw",
        "PhysicsEntranceRaw",
        "MathsCorrect",
        "PhysicsCorrect"
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = 0

    st.write("Total Candidates:", len(df))

    st.write(
        df[
            [
                "RollNo",
                "MathsEntranceRaw",
                "PhysicsEntranceRaw",
                "MathsCorrect",
                "PhysicsCorrect"
            ]
        ].head(10)
    )
    df = df.sort_values(
        by=[
            "IndexMark",
            "MathsEntranceRaw",
            "PhysicsEntranceRaw",
            "NormMath",
            "NormPhy",
            "MathsCorrect",
            "PhysicsCorrect",
            "DOB"
        ],
        ascending=[
            False,  # IndexMark
            False,  # Maths Entrance
            False,  # Physics Entrance
            False,  # Normalized Maths
            False,  # Normalized Physics
            False,  # Maths Correct
            False,  # Physics Correct
            True    # Older candidate
        ]
    )
    st.write(
        df[
            [
                "RollNo",
                "MathsEntranceRaw",
                "PhysicsEntranceRaw",
                "MathsCorrect",
                "PhysicsCorrect"
            ]
        ].head()
    )
    df = df.drop_duplicates(
        subset=["ApplNo"],
        keep="first"
    )
    # -------------------------------------------------
    # Rank
    # -------------------------------------------------

    df["ERank"] = range(
        1,
        len(df) + 1
    )

    # -------------------------------------------------
    # Output
    # -------------------------------------------------

    result = df[
        [
            "ERank",
            "ApplNo",
            "RollNo",
            "Name",
            "BOARD",
            "YEARPASS",
            "NormMath",
            "NormPhy",
            "NormChem",
            "PlusTwoScore",
            "Norm_Score",
            "IndexMark"
        ]
    ]

    st.subheader("Engineering Rank List")

    st.dataframe(
        result,
        use_container_width=True,
        height=700
    )

    st.metric(
        "Candidates Ranked",
        len(result)
    )

    csv = result.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download EngineeringRankList.csv",
        data=csv,
        file_name="EngineeringRankList.csv",
        mime="text/csv"
    )
