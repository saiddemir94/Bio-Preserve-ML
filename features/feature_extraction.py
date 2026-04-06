charge_map = {
    "K": 1,
    "R": 1,
    "H": 1,
    "D": -1,
    "E": -1,
}

hydrophobic = {"A", "V", "I", "L", "M", "F", "W", "Y"}
key_amino_acids = {"K", "R", "L", "I", "F"}
valid_amino_acids = {
    "A",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "V",
    "W",
    "Y",
}


def extract_features(sequence):
    normalized_sequence = sequence.strip().upper()

    if not normalized_sequence:
        raise ValueError("Sequence cannot be empty.")

    invalid_amino_acids = sorted(set(normalized_sequence) - valid_amino_acids)
    if invalid_amino_acids:
        invalid_text = ", ".join(invalid_amino_acids)
        raise ValueError(f"Sequence contains invalid amino acids: {invalid_text}")

    length = len(normalized_sequence)
    net_charge = sum(charge_map.get(amino_acid, 0) for amino_acid in normalized_sequence)
    hydrophobic_count = sum(
        1 for amino_acid in normalized_sequence if amino_acid in hydrophobic
    )
    key_amino_acid_count = sum(
        1 for amino_acid in normalized_sequence if amino_acid in key_amino_acids
    )

    return {
        "length": length,
        "net_charge": net_charge,
        "hydrophobic_ratio": hydrophobic_count / length,
        "key_amino_acid_ratio": key_amino_acid_count / length,
    }


if __name__ == "__main__":
    example_sequence = "KKLRLLRIFKFLRLLKIFRK"
    print(extract_features(example_sequence))
