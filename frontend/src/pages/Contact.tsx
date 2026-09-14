import PageHeader from '@/components/public/PageHeader';
import ContactFormSection from '@/components/contact/ContactFormSection';
import MapSection from '@/components/contact/MapSection';

const breadcrumbs = [
  { name: 'Home', path: '/' },
  { name: 'Contact', path: '/contact' },
];

export function ContactPage() {
  return (
    <>
      <PageHeader title="Contact" breadcrumbs={breadcrumbs} />
      <ContactFormSection />
      <MapSection />
    </>
  );
}
