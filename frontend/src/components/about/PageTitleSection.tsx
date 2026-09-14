import PageHeader from "@/components/public/PageHeader";
export default function PageTitleSection() {
  return (
    <PageHeader
      title="Learning with purpose."
      breadcrumbs={[
        { name: "Home", path: "/" },
        { name: "About us", path: "/about" },
      ]}
    />
  );
}
