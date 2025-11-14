// File: src/Home.jsx
import React from "react";
import Hero from "../components/Hero.jsx";
import Features from "../components/Features.jsx";
import Testimonials from "../components/Testimonials.jsx";
import Pricing from "../components/Pricing.jsx";
import CTASection from "../components/CTASection.jsx";

const Home = () => (
  <>
    <Hero />
    <Features />
    <Testimonials />
    <Pricing />
    <CTASection />
  </>
);

export default Home;
