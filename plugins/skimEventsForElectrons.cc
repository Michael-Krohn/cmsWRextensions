#ifndef skimEventsForElectrons_included
#define skimEventsForElectrons_included 1
// -*- C++ -*-
//
// Package:    ExoAnalysis/skimEventsForElectrons
// Class:      skimEventsForElectrons
// 
/**\class skimEventsForElectrons skimEventsForElectrons.cc ExoAnalysis/skimEventsForElectrons/plugins/skimEventsForElectrons.cc

 Description: [one line class summary]

 Implementation:
     [Notes on implementation]
*/
//
// Original Author:  Andrew Evans
//         Created:  Tue, 05 Sep 2017 15:23:17 GMT
//
//


// system include files
#include <memory>
#include <vector>
#include <iostream>

// user include files
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDFilter.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"

#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/StreamID.h"

#include "DataFormats/PatCandidates/interface/Jet.h"
#include "DataFormats/PatCandidates/interface/Electron.h"
#include "SimDataFormats/GeneratorProducts/interface/GenEventInfoProduct.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"

//ROOT includes
#include "TH1D.h"

//
//local includes
#include "ExoAnalysis/cmsWRextensions/interface/eventBits.h"
#include "ExoAnalysis/cmsWRextensions/interface/eventHistos.h"
#include "ExoAnalysis/cmsWRextensions/interface/tools.h"

//
// class declaration
//

class skimEventsForElectrons : public edm::stream::EDFilter<> {
  public:
    explicit skimEventsForElectrons(const edm::ParameterSet&);
    ~skimEventsForElectrons();

    static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

  private:
    virtual void beginStream(edm::StreamID) override;
    virtual bool filter(edm::Event&, const edm::EventSetup&) override;
    virtual void endStream() override;

    //virtual void beginRun(edm::Run const&, edm::EventSetup const&) override;
    //virtual void endRun(edm::Run const&, edm::EventSetup const&) override;
    //virtual void beginLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&) override;
    //virtual void endLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&) override;

     // ----------member data ---------------------------

    eventHistos m_allEvents;
    edm::EDGetToken m_genEventInfoToken;
    edm::EDGetToken m_recoElecToken;
    edm::EDGetToken m_AK8recoJetsToken;
    edm::EDGetToken m_metToken;
    bool m_isMC;
};

//
// constants, enums and typedefs
//

//
// static data member definitions
//

//
// constructors and destructor
//
skimEventsForElectrons::skimEventsForElectrons(const edm::ParameterSet& iConfig) :
  m_recoElecToken (consumes<std::vector<pat::Electron>> (iConfig.getParameter<edm::InputTag>("recoElectrons"))),
  m_AK8recoJetsToken (consumes<std::vector<pat::Jet>> (iConfig.getParameter<edm::InputTag>("AK8recoJets"))),
  m_metToken (consumes<std::vector<pat::MET>> (iConfig.getParameter<edm::InputTag>("met"))),  
  m_isMC (iConfig.getUntrackedParameter<bool>("isMC",true))
{
  //now do what ever initialization is needed
  edm::Service<TFileService> fs;
  m_allEvents.book((fs->mkdir("allEvents")), 4);
  if(m_isMC) m_genEventInfoToken = consumes<GenEventInfoProduct> (iConfig.getParameter<edm::InputTag>("genInfo"));

}


skimEventsForElectrons::~skimEventsForElectrons()
{
 
   // do anything here that needs to be done at destruction time
   // (e.g. close files, deallocate resources etc.)

}


//
// member functions
//

// ------------ method called on each new Event  ------------
bool
skimEventsForElectrons::filter(edm::Event& iEvent, const edm::EventSetup& iSetup)
{
  eventBits myRECOevent;
  if(m_isMC) {
    edm::Handle<GenEventInfoProduct> eventInfo;
    iEvent.getByToken(m_genEventInfoToken, eventInfo);
    myRECOevent.weight = eventInfo->weight();
  } else {
  myRECOevent.weight = 1;
  }
  
  m_allEvents.fill(myRECOevent);
  std::cout <<"THIS EVENT HAS A WEIGHT OF: "<<myRECOevent.weight <<std::endl;

  int elecPass = 0;
  edm::Handle<std::vector<pat::Electron>> recoElectrons;
  iEvent.getByToken(m_recoElecToken, recoElectrons);
  for(std::vector<pat::Electron>::const_iterator iElectron = recoElectrons->begin(); iElectron != recoElectrons->end(); iElectron++) {
    if (iElectron->pt() < 150 || fabs(iElectron->eta()) > 2.8) continue;
    elecPass++;
  }

  int jetPass = 0;
  edm::Handle<std::vector<pat::Jet>> ak8recoJets;
  iEvent.getByToken(m_AK8recoJetsToken, ak8recoJets);
  for(std::vector<pat::Jet>::const_iterator iJet = ak8recoJets->begin(); iJet != ak8recoJets->end(); iJet++) {
    if (iJet->pt() < 150 || fabs(iJet->eta()) > 2.8) continue;
    jetPass++;
  }

  if (jetPass > 0 && elecPass > 0) {
    std::cout <<"PASSES"<<std::endl;
    return true; 
  }
  std::cout << "FAILS"<<std::endl;
  return false;
}

// ------------ method called once each stream before processing any runs, lumis or events  ------------
void
skimEventsForElectrons::beginStream(edm::StreamID)
{
}

// ------------ method called once each stream after processing all runs, lumis and events  ------------
void
skimEventsForElectrons::endStream() {
}

// ------------ method called when starting to processes a run  ------------
/*
void
skimEventsForElectrons::beginRun(edm::Run const&, edm::EventSetup const&)
{ 
}
*/
 
// ------------ method called when ending the processing of a run  ------------
/*
void
skimEventsForElectrons::endRun(edm::Run const&, edm::EventSetup const&)
{
}
*/
 
// ------------ method called when starting to processes a luminosity block  ------------
/*
void
skimEventsForElectrons::beginLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&)
{
}
*/
 
// ------------ method called when ending the processing of a luminosity block  ------------
/*
void
skimEventsForElectrons::endLuminosityBlock(edm::LuminosityBlock const&, edm::EventSetup const&)
{
}
*/
 
// ------------ method fills 'descriptions' with the allowed parameters for the module  ------------
void
skimEventsForElectrons::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  //The following says we do not know what parameters are allowed so do no validation
  // Please change this to state exactly what you do use, even if it is no parameters
  edm::ParameterSetDescription desc;
  desc.setUnknown();
  descriptions.addDefault(desc);
}
//define this as a plug-in
DEFINE_FWK_MODULE(skimEventsForElectrons);
#endif
