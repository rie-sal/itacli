// itacli translation popover: a frosted floating panel near the cursor.
// Native LOOK (NSVisualEffectView) with itacli's own translation, since the
// system Translate popover cannot be summoned programmatically.
import AppKit

let text = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let font = NSFont.systemFont(ofSize: 16, weight: .medium)
let attrs: [NSAttributedString.Key: Any] = [.font: font]
let textW = min(560.0, max(180.0, (text as NSString).size(withAttributes: attrs).width + 36))
let w = textW, h: CGFloat = 60

let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: w, height: h),
                    styleMask: [.borderless, .nonactivatingPanel],
                    backing: .buffered, defer: false)
panel.level = .floating
panel.isOpaque = false
panel.backgroundColor = .clear
panel.hasShadow = true

let vev = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: w, height: h))
vev.material = .hudWindow
vev.state = .active
vev.wantsLayer = true
vev.layer?.cornerRadius = 14
vev.autoresizingMask = [.width, .height]

let label = NSTextField(labelWithString: text)
label.font = font
label.lineBreakMode = .byTruncatingTail
label.frame = NSRect(x: 18, y: (h - 22) / 2, width: w - 36, height: 22)
vev.addSubview(label)
panel.contentView = vev

let m = NSEvent.mouseLocation
panel.setFrameOrigin(NSPoint(x: m.x - 20, y: m.y - h - 12))
panel.orderFrontRegardless()
RunLoop.current.run(until: Date().addingTimeInterval(3.0))
