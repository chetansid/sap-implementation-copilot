from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfbase.pdfmetrics import stringWidth

OUT = "output/pdf/vendor_master_interface_functional_specification.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleBlue", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=colors.HexColor("#123B5D"), alignment=TA_LEFT, spaceAfter=10))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=12, leading=17, textColor=colors.HexColor("#51616E")))
styles.add(ParagraphStyle(name="H1Blue", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#123B5D"), spaceBefore=12, spaceAfter=7))
styles.add(ParagraphStyle(name="H2Blue", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#1E6388"), spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.4, leading=11.2, spaceAfter=4))
styles.add(ParagraphStyle(name="TableText", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9))
styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=colors.white))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8.8, leading=12, textColor=colors.HexColor("#274C5E")))

def p(text, style="BodySmall"):
    return Paragraph(text, styles[style])

def table(headers, rows, widths):
    data = [[p(h, "TableHead") for h in headers]] + [[p(str(c), "TableText") for c in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#123B5D")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B9C7D0")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F7FA")]),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return t

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5E0E6")); canvas.line(0.55*inch, 0.48*inch, 7.95*inch, 0.48*inch)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.HexColor("#51616E"))
    canvas.drawString(0.55*inch, 0.30*inch, "Sample RICEFW Functional Specification - Vendor Master Interface")
    canvas.drawRightString(7.95*inch, 0.30*inch, "Page %d" % doc.page)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=letter, rightMargin=0.55*inch, leftMargin=0.55*inch, topMargin=0.55*inch, bottomMargin=0.68*inch)
story = []

# Cover
story += [Spacer(1, 0.52*inch), p("FUNCTIONAL SPECIFICATION", "Subtitle"), Spacer(1, 0.10*inch), p("Vendor Master\nInterface", "TitleBlue"), p("Legacy Procurement Hub to SAP S/4HANA", "Subtitle"), Spacer(1, 0.36*inch)]
story.append(Table([[p("RICEFW object", "TableText"), p("Interface (I)", "TableText")], [p("Document ID", "TableText"), p("FS-INT-VM-001", "TableText")], [p("Version", "TableText"), p("1.0 - Sample", "TableText")], [p("Status", "TableText"), p("Draft for design review", "TableText")], [p("Prepared for", "TableText"), p("SAP S/4HANA Implementation Program", "TableText")]], colWidths=[1.45*inch, 4.75*inch], style=TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E7F0F5")),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#B9C7D0")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)])))
story += [Spacer(1, 0.38*inch), p("Purpose", "H1Blue"), p("This sample specification defines the inbound interface that creates and changes supplier business partners in SAP S/4HANA from the legacy Procurement Hub. It is intended as a reusable project template; organization codes, endpoints, and field rules must be confirmed during design.", "Callout"), Spacer(1, 0.2*inch), p("Confidential - Sample implementation artifact", "Subtitle"), PageBreak()]

# 1 Overview
story += [p("1. Business Overview", "H1Blue"), p("The Procurement Hub remains the system of record for vendor onboarding and maintenance during the transition period. Approved vendor records are sent to SAP S/4HANA so that purchase orders, invoices, and payments can be processed against a consistent supplier master. In S/4HANA, suppliers are maintained as Business Partners with supplier roles.")]
story += [p("1.1 Scope", "H2Blue"), table(["In scope", "Out of scope"], [["Create and change supplier general, company code, purchasing, address, bank, tax, and contact data.", "Vendor deactivation, duplicate cleansing, workflow approval, and payment execution."], ["Synchronous validation response and nightly reconciliation report.", "Historical vendor migration and non-supplier business partner categories."]], [3.5*inch, 3.5*inch])]
story += [p("1.2 Assumptions and Dependencies", "H2Blue"), table(["ID", "Assumption / dependency", "Owner"], [["A-01", "Legacy vendor ID is stable and is stored in SAP as an external BP identification.", "Data Governance"], ["A-02", "Company code, purchasing organization, payment terms, reconciliation account, and tax code mapping are approved before SIT.", "Finance / Procurement"], ["A-03", "SAP Integration Suite routes messages and applies mutual TLS authentication.", "Integration"], ["A-04", "SAP MDG is not in scope for this initial release; changes originate in the legacy system.", "Program"], ["A-05", "Bank details are sent only for vendors authorized by the legacy approval workflow.", "Treasury"]], [0.5*inch, 5.25*inch, 1.25*inch])]
story += [p("1.3 Success Criteria", "H2Blue"), p("A valid vendor is created or updated within 15 minutes of approval; malformed messages are rejected without partial master-data updates; and daily source-to-target counts reconcile to 100 percent after approved reprocessing."), PageBreak()]

# 2 design
story += [p("2. Interface Design", "H1Blue"), table(["Attribute", "Design"], [["Interface name", "LEGACY_VENDOR_TO_S4_BP"], ["Direction", "Inbound to SAP S/4HANA"], ["Trigger / frequency", "Near real-time event after vendor approval or change; scheduled reconciliation at 02:00 local time."], ["Transport", "HTTPS REST through SAP Integration Suite; JSON UTF-8 payload; mutual TLS and OAuth 2.0 client credentials."], ["SAP processing", "Integration flow validates/enriches, then invokes the SAP Business Partner supplier API / inbound service."], ["Idempotency", "SourceVendorId + SourceChangeTimestamp. Replayed messages with an unchanged key are acknowledged without duplicate creation."], ["Volume", "Estimated 300 creates/changes per business day; peak 50 messages per 15 minutes."], ["Retention", "Payload and application logs retained 90 days; bank values masked in operational logs."]], [1.55*inch, 5.45*inch])]
story += [p("2.1 Processing Flow", "H2Blue"), p("1. Legacy approval publishes VendorUpsert.  2. Integration Suite authenticates, validates schema, and translates codes.  3. SAP determines the existing Business Partner by external legacy ID.  4. SAP creates or updates BP general data, supplier company code, and purchasing views in one logical unit.  5. A response returns the BP number, processing status, and any business errors.  6. Failed records enter the support queue for correction and replay.", "BodySmall")]
story += [p("2.2 Key Business Rules", "H2Blue"), table(["Rule", "Description"], [["BR-01", "Legal name, country, language, and supplier account group/category are mandatory for create."], ["BR-02", "If SourceVendorId already exists, update the related Business Partner; do not create a new BP."], ["BR-03", "Company code data is required when payment terms, reconciliation account, or withholding-tax data is supplied."], ["BR-04", "Bank account changes require a source approval flag = Y; otherwise reject with error VM-120."], ["BR-05", "ISO country and currency codes must be valid; unmapped legacy codes are rejected."], ["BR-06", "Blank source values do not clear SAP values unless ClearIndicator = Y for the specific field group."]], [0.75*inch, 6.25*inch]), PageBreak()]

# Mapping
story += [p("3. Field Mapping", "H1Blue"), p("The mapping below represents the minimum viable supplier payload. Final SAP API property names and controlled values are to be confirmed in the interface technical design.")]
mapping = [["Header.sourceVendorId", "BP Identification (LEGACY_VENDOR)", "Char 20", "Y", "External unique key; immutable."], ["Header.changeTimestamp", "Extension: Source Change Timestamp", "ISO 8601", "Y", "Used for idempotency and audit."], ["General.legalName", "BP Organization Name 1", "Char 80", "Y", "Trim and collapse multiple spaces."], ["General.searchTerm", "BP Search Term 1", "Char 20", "N", "Default to first 20 chars of legal name."], ["General.language", "BP Correspondence Language", "ISO 639-1", "Y", "Map legacy language code."], ["Address.country", "BP Address Country", "ISO 3166-1", "Y", "Validate against SAP country table."], ["Address.city / postalCode", "BP Address City / Postal Code", "Char 40 / 10", "Y", "Postal code format by country."], ["Tax.taxNumber", "BP Tax Number 1", "Char 30", "Conditional", "Mandatory where country tax registration requires it."], ["Company.companyCode", "Supplier Company Code", "Char 4", "Y", "Must be active SAP company code."], ["Company.reconAccount", "Supplier Reconciliation Account", "Char 10", "Y", "Map legacy liability class."], ["Company.paymentTerms", "Supplier Payment Terms", "Char 4", "Y", "Map approved payment term."], ["Purchasing.purchOrg", "Supplier Purchasing Organization", "Char 4", "Y", "At least one purchasing organization."], ["Purchasing.orderCurrency", "Supplier Order Currency", "ISO 4217", "N", "Default from purchasing organization."], ["Bank.iban / accountNo", "BP Bank Detail", "Char 34 / 18", "Conditional", "One is required when bank data is sent."]]
story.append(table(["Legacy JSON field", "SAP S/4HANA target", "Format", "Req.", "Transformation / validation"], mapping, [1.3*inch, 1.55*inch, 0.78*inch, 0.57*inch, 2.8*inch]))
story += [Spacer(1, 0.1*inch), p("Sample Payload", "H2Blue"), p('<font name="Courier" size="7">{"sourceVendorId":"L-104582","changeTimestamp":"2026-10-18T14:30:00Z","legalName":"Acme Industrial Supply LLC","companyCode":"1000","purchOrg":"1000","paymentTerms":"0001"}</font>', "BodySmall"), PageBreak()]

# errors and operations
story += [p("4. Error Handling and Operations", "H1Blue"), table(["Category", "Handling", "Response / ownership"], [["Schema or security failure", "Reject before SAP invocation; log correlation ID and error code.", "HTTP 400/401/403; legacy integration support."], ["Business validation failure", "Do not update SAP. Place message in exception queue with field-level detail.", "HTTP 422; master-data analyst corrects source or mapping."], ["SAP technical failure", "Retry automatically up to 3 times with exponential backoff. Queue after final failure.", "HTTP 500/503; SAP basis / integration support."], ["Partial processing", "Not permitted. General, company code, purchasing, and bank updates execute atomically where supported.", "Return VM-500; manual review."], ["Duplicate / replay", "Compare idempotency key and last applied timestamp.", "HTTP 200 with status DUPLICATE_IGNORED."]], [1.25*inch, 3.65*inch, 2.1*inch])]
story += [p("4.1 Error Codes", "H2Blue"), table(["Code", "Meaning", "Corrective action"], [["VM-101", "Required legal name is missing.", "Populate General.legalName and replay."], ["VM-115", "Company code is not mapped or inactive.", "Correct mapping or activate valid company code."], ["VM-120", "Bank update lacks approval flag.", "Obtain approval in source and resend."], ["VM-130", "Tax number format is invalid for country.", "Correct tax registration data."], ["VM-500", "Unexpected SAP processing error.", "Review correlation ID and SAP application log."]], [0.75*inch, 3.1*inch, 3.15*inch])]
story += [p("4.2 Monitoring and Reconciliation", "H2Blue"), p("Integration monitoring alerts the support team for messages in error longer than 30 minutes. A daily reconciliation compares approved source changes, successful SAP responses, failed messages, and queued retries by date and source vendor ID. Any unmatched record is investigated within one business day."), p("4.3 Security and Controls", "H2Blue"), p("Transport uses TLS 1.2 or higher. Service credentials are held in the secure credential store. Access to payload monitoring is limited to integration support and authorized master-data users. Operational logs mask bank account and tax-number values. All create/change events retain the source system ID, correlation ID, timestamp, and SAP user/service ID."), PageBreak()]

# Acceptance
story += [p("5. Test Scenarios and Acceptance", "H1Blue"), table(["ID", "Scenario", "Expected result"], [["T-01", "Create a domestic supplier with one company code and purchasing organization.", "BP and supplier roles created; response contains SAP BP number."], ["T-02", "Update an existing supplier address and payment terms.", "Existing BP updated; no duplicate BP created."], ["T-03", "Send a missing legal name.", "Message rejected with VM-101; SAP unchanged."], ["T-04", "Send bank data without source approval.", "Message rejected with VM-120; bank details unchanged."], ["T-05", "Replay a successfully processed message.", "Acknowledged as DUPLICATE_IGNORED; no duplicate update."], ["T-06", "Simulate SAP unavailable.", "Automatic retry occurs; message queues after third failure."], ["T-07", "Run daily reconciliation with one deliberately failed record.", "Report identifies record and its correlation ID."], ["T-08", "Validate role-based log access.", "Unauthorized user cannot view unmasked payload data."]], [0.55*inch, 3.05*inch, 3.4*inch])]
story += [p("5.1 Acceptance Criteria", "H2Blue"), p("Business and IT approve the interface when all critical scenarios pass, mappings are signed off, no high-severity security findings remain, and reconciliation demonstrates complete traceability from source approval through SAP processing."), p("6. Approvals", "H1Blue"), table(["Role", "Name", "Approval", "Date"], [["Business Process Owner", "________________________", "________________", "____________"], ["Finance Data Owner", "________________________", "________________", "____________"], ["SAP Functional Lead", "________________________", "________________", "____________"], ["Integration Lead", "________________________", "________________", "____________"]], [1.55*inch, 2.35*inch, 1.45*inch, 1.25*inch])]
story += [Spacer(1, 0.18*inch), p("Document Change Log", "H2Blue"), table(["Version", "Date", "Author", "Description"], [["1.0", "2026-10-18", "Implementation Team", "Initial sample functional specification."]], [0.9*inch, 1.2*inch, 1.8*inch, 2.7*inch])]

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
