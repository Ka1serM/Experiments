import colour
import numpy as np

# uv add --dev colour-science

# Fraunhofer C, d, F in nm
lines = np.array([656.0, 587.0, 486.0])

# Match PBRT's visible range / 1 nm grid.
shape = colour.SpectralShape(360, 830, 1)

cmfs = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"].copy().align(shape)
d65 = colour.SDS_ILLUMINANTS["D65"].copy().align(shape)

wavelengths = cmfs.wavelengths
xyz = cmfs.values  # shape: [n, 3]
illum = d65.values  # shape: [n]

xyz_at_lines = np.stack(
    [
        np.interp(lines, wavelengths, xyz[:, 0]),
        np.interp(lines, wavelengths, xyz[:, 1]),
        np.interp(lines, wavelengths, xyz[:, 2]),
    ]
)

d65_at_lines = np.interp(lines, wavelengths, illum)

# A maps three unknown quadrature weights to XYZ.
A = xyz_at_lines * d65_at_lines

# Full D65 white target over the visible range.
target = np.sum(xyz * illum[:, None], axis=0)

weights = np.linalg.solve(A, target)

# If runtime samples C/d/F uniformly, PBRT's estimator divides by PDF.
# So use effective_pdf = q / weight.
q = np.full(3, 1 / 3)
effective_pdf = q / weights

print("weights C,d,F:", weights)
print("normalized weights:", weights / weights.sum())
print("effective PDFs:", effective_pdf)
print("target:", target)
print("quadrature:", A @ weights)
