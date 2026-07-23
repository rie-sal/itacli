// itacli translation popover - an ORIGINAL, approximate look (public AppKit).
// The system Translate popover is a private, closed-source framework and cannot
// be summoned or copied; this just resembles it: a frosted rounded panel near
// the cursor with the source word above the translation.
import AppKit

let args = CommandLine.arguments
let source = args.count > 1 ? args[1] : ""
let translation = args.count > 2 ? args[2] : (args.count > 1 ? args[1] : "")

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let transFont = NSFont.systemFont(ofSize: 17, weight: .semibold)
let srcFont = NSFont.systemFont(ofSize: 12, weight: .regular)
let tw = (translation as NSString).size(withAttributes: [.font: transFont]).width
let sw = (source as NSString).size(withAttributes: [.font: srcFont]).width
let w = min(560.0, max(180.0, max(tw, sw) + 40))
let h: CGFloat = 66

let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: w, height: h),
                    styleMask: [.borderless, .nonactivatingPanel],
                    backing: .buffered, defer: false)
panel.level = .floating
panel.isOpaque = false
panel.backgroundColor = .clear
panel.hasShadow = true

let vev = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: w, height: h))
vev.material = .popover
vev.state = .active
vev.wantsLayer = true
vev.layer?.cornerRadius = 12
vev.layer?.borderWidth = 0.5
vev.layer?.borderColor = NSColor.separatorColor.cgColor
vev.autoresizingMask = [.width, .height]

let srcLabel = NSTextField(labelWithString: source)
srcLabel.font = srcFont
srcLabel.textColor = .secondaryLabelColor
srcLabel.lineBreakMode = .byTruncatingTail
srcLabel.frame = NSRect(x: 18, y: h - 30, width: w - 36, height: 16)

let transLabel = NSTextField(labelWithString: translation)
transLabel.font = transFont
transLabel.lineBreakMode = .byTruncatingTail
transLabel.frame = NSRect(x: 18, y: 14, width: w - 36, height: 24)

vev.addSubview(srcLabel)
vev.addSubview(transLabel)
panel.contentView = vev

let m = NSEvent.mouseLocation
panel.setFrameOrigin(NSPoint(x: m.x - 20, y: m.y - h - 12))
panel.orderFrontRegardless()
RunLoop.current.run(until: Date().addingTimeInterval(3.2))
