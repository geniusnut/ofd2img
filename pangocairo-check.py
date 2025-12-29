import cairo
import gi
import sys

gi.require_version("PangoCairo", "1.0")
gi.require_version("Pango", "1.0")
from gi.repository import PangoCairo, Pango

print("=== Cairo and PangoCairo Compatibility Check ===")
print("Cairo version:", cairo.version)
print("Cairo library:", cairo.cairo_version())
print(
    "PangoCairo version:",
    PangoCairo.__version__ if hasattr(PangoCairo, "__version__") else "Unknown",
)
print("Python version:", sys.version)
print()

# Test creating layout with PangoCairo
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
cr = cairo.Context(surface)

print("Cairo context type:", type(cr))
print("Cairo context:", cr)
print()

# Check if we can use PangoCairo directly
print("--- Test 1: PangoCairo.create_layout(cr) ---")
try:
    layout = PangoCairo.create_layout(cr)
    print("SUCCESS: PangoCairo.create_layout(cr) worked!")
except Exception as e:
    print(f"FAILED: PangoCairo.create_layout(cr) - {e}")
    print(
        "This is expected on some Ubuntu versions due to GObject introspection incompatibility"
    )

# Alternative approach: Create Pango context with font map
print("\n--- Test 2: Using font_map.create_context() + PangoCairo functions ---")
try:
    font_map = PangoCairo.font_map_get_default()
    pango_context = font_map.create_context()
    layout = Pango.Layout.new(pango_context)
    layout.set_text("Test", -1)
    desc = Pango.FontDescription.from_string("monospace 12")
    layout.set_font_description(desc)

    # Now use PangoCairo functions with the layout and cairo context
    print("  - Attempting PangoCairo.update_layout(cr, layout)...")
    PangoCairo.update_layout(cr, layout)
    print("  SUCCESS: PangoCairo.update_layout(cr, layout) worked!")

    # Try to show the layout
    print("  - Attempting PangoCairo.show_layout(cr, layout)...")
    cr.move_to(10, 10)
    PangoCairo.show_layout(cr, layout)
    print("  SUCCESS: PangoCairo.show_layout(cr, layout) worked!")
    print("\nRECOMMENDATION: Use this approach in surface.py")

except Exception as e:
    print(f"  FAILED: {e}")
    print("  This means PangoCairo functions won't work on this system")
    print("  RECOMMENDATION: Use Cairo's native text rendering instead")
    print()

    # Test Cairo native text rendering
    print("--- Test 3: Using Cairo's native text rendering ---")
    try:
        cr.select_font_face(
            "monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )
        cr.set_font_size(12)
        cr.move_to(10, 10)
        cr.show_text("Test")
        print("  SUCCESS: Cairo native text rendering works!")
        print("  This is the fallback solution for surface.py")
    except Exception as e2:
        print(f"  FAILED: {e2}")

print("\n=== Summary ===")
print("If Test 2 succeeded: PangoCairo functions work on this system")
print("If Test 2 failed but Test 3 succeeded: Use Cairo native text rendering")
print("If both failed: Check Cairo and Pango installation")
