frappe.ui.form.on("Job Requisition", {
  refresh(frm) {
    if (frm.is_new()) {
      return;
    }

    frm.add_custom_button("刷新代理发布包", async () => {
      await frappe.call({
        method: "aihr.api.recruitment.sync_job_requisition_agency_brief",
        args: { job_requisition: frm.doc.name, save: 1 },
        freeze: true,
        freeze_message: "正在刷新代理发布包...",
      });
      await frm.reload_doc();
      frappe.show_alert({ message: "代理发布包已刷新", indicator: "green" });
    });

    if (frm.doc.aihr_agency_brief) {
      frm.add_custom_button("复制代理发布包", () => {
        frappe.utils.copy_to_clipboard(frm.doc.aihr_agency_brief);
        frappe.show_alert({ message: "代理发布包已复制", indicator: "green" });
      });
    }
  },
});
