import React from "react";
import Hero from "../components/Hero";
import Features from "../components/Features";
//import Testimonials from "../components/Testimonials";
import Pricing from "../components/Pricing";
import CTASection from "../components/CTASection";
import { SHOW_PRICING } from "../config/accessMode.js";

const Home = () => (
  <>
    <Hero />
    <Features />
    {SHOW_PRICING ? <Pricing /> : null}
    <CTASection />
  </>
);

export default Home;